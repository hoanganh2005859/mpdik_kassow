"""Targeted tests for release packaging (task section 10): checksum manifest integrity and the
public-ZIP protected-field scan. Uses a small synthetic release-shaped directory -- no Dataset v2
working root required.
"""

import json

import numpy as np
import pytest

from evaluation_v2.release_builder import RELEASE_VERSION, write_checksum_manifest
from evaluation_v2.release_packaging import extract_and_validate_public_zip, zip_directory
from utils.npz_utils import save_npz


def _fake_release(root, *, leak_protected=False):
    root.mkdir(parents=True, exist_ok=True)
    (root / "VERSION").write_text(RELEASE_VERSION + "\n", encoding="utf-8")
    (root / "tier1_point_ik").mkdir()
    (root / "trials").mkdir()
    (root / "trajectories").mkdir()
    splits = ["development", "validation", "frozen_test"]
    for split in splits:
        arrays = {"sample_id": np.arange(3), "q_initial": np.zeros((3, 7))}
        if leak_protected and split == "frozen_test":
            arrays["q_target_reference"] = np.zeros((3, 7))
        save_npz(root / "tier1_point_ik" / f"{split}.npz", arrays)
        save_npz(root / "trials" / f"{split}.npz", {"trial_id": np.arange(2)})
    (root / "DATASET_MANIFEST.json").write_text(
        json.dumps({"version": RELEASE_VERSION, "splits": splits, "counts": {"point_ik_total": 9}}),
        encoding="utf-8",
    )
    return root


def test_checksum_manifest_matches_files_on_disk(tmp_path):
    release = _fake_release(tmp_path / "release")
    manifest_path = write_checksum_manifest(release)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    from utils.file_checksum import sha256_file

    for entry in manifest["files"]:
        assert sha256_file(release / entry["path"]) == entry["sha256"]


def test_extract_and_validate_public_zip_passes_when_clean(tmp_path):
    release = _fake_release(tmp_path / "release")
    write_checksum_manifest(release)
    zip_path = zip_directory(release, tmp_path / "out.zip")
    report = extract_and_validate_public_zip(zip_path, tmp_path / "extract")
    assert report["checksum_pass"]
    assert report["loader_ok"]
    assert report["isolation_pass"]
    assert report["protected_leaks"] == []


def test_extract_and_validate_public_zip_catches_protected_leak(tmp_path):
    release = _fake_release(tmp_path / "release", leak_protected=True)
    write_checksum_manifest(release)
    zip_path = zip_directory(release, tmp_path / "out.zip")
    report = extract_and_validate_public_zip(zip_path, tmp_path / "extract")
    assert not report["isolation_pass"]
    assert any("frozen_test" in leak for leak in report["protected_leaks"])


def test_zip_marker_text_written_for_protected_archive(tmp_path):
    src = tmp_path / "protected"
    src.mkdir()
    (src / "note.json").write_text("{}", encoding="utf-8")
    zip_path = zip_directory(src, tmp_path / "protected.zip", marker_text="INTERNAL_PROTECTED_VALIDATION_NOT_FOR_EVALUATION")
    import zipfile

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert any("INTERNAL_PROTECTED_VALIDATION_NOT_FOR_EVALUATION" in n for n in names)
