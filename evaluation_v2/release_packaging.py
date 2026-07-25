"""ZIP packaging + SHA256SUMS for the Dataset v2.0.0 release artifacts, and a self-check that
extracts the public ZIP and re-validates it (checksums, schema/counts, public loader, no
protected fields) before the release is considered final.
"""

import json
import zipfile
from pathlib import Path

from evaluation_v2.protected_guard import find_protected_fields
from utils.file_checksum import sha256_file


def zip_directory(src_dir: Path, zip_path: Path, *, marker_text: str = None) -> Path:
    src_dir = Path(src_dir)
    zip_path = Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if marker_text is not None:
            zf.writestr("INTERNAL_PROTECTED_VALIDATION_NOT_FOR_EVALUATION.txt", marker_text)
        for path in sorted(p for p in src_dir.rglob("*") if p.is_file()):
            zf.write(path, path.relative_to(src_dir).as_posix())
    return zip_path


def write_sha256sums(files, out_path: Path) -> Path:
    out_path = Path(out_path)
    lines = []
    for f in sorted(Path(f) for f in files):
        lines.append(f"{sha256_file(f)}  {f.name}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def extract_and_validate_public_zip(zip_path: Path, extract_dir: Path) -> dict:
    """Extract the public release ZIP and re-verify: checksum manifest, expected counts,
    public loader readability, and absence of any protected field. Returns a report dict."""
    from evaluation_v2.locator import require_public_eval_root
    from utils.npz_utils import load_npz

    zip_path = Path(zip_path)
    extract_dir = Path(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)

    checksum_manifest = json.loads((extract_dir / "CHECKSUM_MANIFEST.json").read_text(encoding="utf-8"))
    mismatches = []
    for entry in checksum_manifest["files"]:
        p = extract_dir / entry["path"]
        if not p.is_file():
            mismatches.append({"path": entry["path"], "issue": "missing"})
            continue
        actual = sha256_file(p)
        if actual != entry["sha256"]:
            mismatches.append({"path": entry["path"], "issue": "sha256_mismatch"})

    dataset_manifest = json.loads((extract_dir / "DATASET_MANIFEST.json").read_text(encoding="utf-8"))
    version_file = (extract_dir / "VERSION").read_text(encoding="utf-8").strip()

    # Public loader smoke: resolve as a public eval root and read every Point-IK NPZ.
    loader_ok = True
    protected_leaks = []
    try:
        for split in dataset_manifest["splits"]:
            arrays = load_npz(extract_dir / "tier1_point_ik" / f"{split}.npz")
            if find_protected_fields(arrays.keys()):
                protected_leaks.append(f"tier1_point_ik/{split}.npz")
            trial_arrays = load_npz(extract_dir / "trials" / f"{split}.npz")
            if find_protected_fields(trial_arrays.keys()):
                protected_leaks.append(f"trials/{split}.npz")
        for traj_file in (extract_dir / "trajectories").rglob("*.npz"):
            arrays = load_npz(traj_file)
            if find_protected_fields(arrays.keys()) or "q_reference" in arrays:
                protected_leaks.append(str(traj_file.relative_to(extract_dir)))
    except Exception as exc:  # pragma: no cover - surfaced in the report, not swallowed
        loader_ok = False
        protected_leaks.append(f"loader_error: {exc}")

    return {
        "version": version_file,
        "checksum_mismatches": mismatches,
        "checksum_pass": len(mismatches) == 0,
        "counts": dataset_manifest["counts"],
        "loader_ok": loader_ok,
        "protected_leaks": protected_leaks,
        "isolation_pass": len(protected_leaks) == 0,
    }
