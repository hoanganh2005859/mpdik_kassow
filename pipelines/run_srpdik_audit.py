"""Read-only metadata/source audit for the SR-PPO-DLS (srpdik) Phase 1 scaffold.

Checks repo/git state, the PDF reference hash, srpdik config parsing, the locked pure-DLS
snapshot (candidate name + source/config hashes), Dataset v1 immutability (checksum-manifest
files unchanged), an optionally-supplied Dataset v2 public root (manifest/checksum file
existence only -- never scanned beyond that, never a sibling directory, never frozen_test
content), that frozen_test access is denied by default, and dependency availability.

Never runs the DLS solver, never runs an evaluation, never generates a dataset.

Usage:
    python -m pipelines.run_srpdik_audit
    python -m pipelines.run_srpdik_audit --dataset-v2-root /path/to/kr810_dataset_v2_public

Exit codes: 0 = audit pass, 1 = integrity/audit failure, 2 = usage/config error.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from srpdik import constants
from srpdik.data.split_guard import is_split_access_allowed
from srpdik.dls_lock import (
    DLSLockVerificationError,
    load_dls_lock,
    verify_candidate_name,
    verify_resolved_parameters_match_live_source,
    verify_source_hashes,
)
from srpdik.exceptions import SRPDIKConfigError
from srpdik.manifests import build_srpdik_config_manifest
from srpdik.paths import repo_root
from utils.file_checksum import sha256_file

_REQUIRED_DEPENDENCIES = ("numpy", "scipy", "mujoco", "pytest")
_OPTIONAL_DEPENDENCIES = ("gymnasium", "stable_baselines3", "torch")


class _Report:
    def __init__(self) -> None:
        self.entries: List[dict] = []

    def record(self, check: str, status: str, detail: str = "") -> None:
        self.entries.append({"check": check, "status": status, "detail": detail})

    def has_failure(self) -> bool:
        return any(entry["status"] == "fail" for entry in self.entries)

    def print_all(self) -> None:
        for entry in self.entries:
            print(f"[{entry['status'].upper():4}] {entry['check']}: {entry['detail']}")


def _git_output(args: List[str], cwd: Path) -> Optional[str]:
    try:
        result = subprocess.run(
            args, cwd=str(cwd), capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _check_repo_root_and_git_state(report: _Report, root: Path) -> None:
    if not root.is_dir():
        report.record("repo_root_and_git_state", "fail", f"repo root not found: {root}")
        return
    commit = _git_output(["git", "rev-parse", "HEAD"], cwd=root)
    dirty = _git_output(["git", "status", "--short"], cwd=root)
    if commit is None:
        report.record(
            "repo_root_and_git_state", "fail", f"repo root {root} is not a readable git repository"
        )
        return
    dirty_count = len(dirty.splitlines()) if dirty else 0
    report.record(
        "repo_root_and_git_state",
        "pass",
        f"root={root} commit={commit} dirty_files={dirty_count}",
    )


def _check_pdf_reference(report: _Report, root: Path) -> None:
    pdf_path = root / constants.PDF_REFERENCE_RELATIVE_PATH
    if not pdf_path.is_file():
        report.record("pdf_reference", "fail", f"PDF reference not found: {pdf_path}")
        return
    actual = sha256_file(pdf_path)
    if actual != constants.PDF_REFERENCE_SHA256:
        report.record(
            "pdf_reference",
            "fail",
            f"sha256 mismatch: expected {constants.PDF_REFERENCE_SHA256}, got {actual}",
        )
        return
    report.record("pdf_reference", "pass", f"sha256 matches ({actual})")


def _check_srpdik_configs(report: _Report) -> None:
    try:
        manifest = build_srpdik_config_manifest()
    except SRPDIKConfigError as exc:
        report.record("srpdik_configs_parse", "fail", str(exc))
        return
    report.record("srpdik_configs_parse", "pass", f"{len(manifest)} config(s) parsed")


def _check_dls_lock(report: _Report) -> None:
    try:
        lock = load_dls_lock()
    except DLSLockVerificationError as exc:
        report.record("dls_lock_parse", "fail", str(exc))
        report.record("dls_lock_source_hashes", "fail", "skipped: lock did not parse")
        report.record("dls_lock_candidate_name", "fail", "skipped: lock did not parse")
        return
    report.record("dls_lock_parse", "pass", "configs/srpdik/dls_locked.json parsed")

    try:
        verify_source_hashes(lock)
        verify_resolved_parameters_match_live_source(lock)
        report.record(
            "dls_lock_source_hashes", "pass", "source/config hashes and resolved_parameters match"
        )
    except DLSLockVerificationError as exc:
        report.record("dls_lock_source_hashes", "fail", str(exc))

    try:
        verify_candidate_name(lock)
        report.record("dls_lock_candidate_name", "pass", lock.get("candidate_name", ""))
    except DLSLockVerificationError as exc:
        report.record("dls_lock_candidate_name", "fail", str(exc))


def _verify_dataset_v1_immutability(root: Path) -> List[str]:
    """Recompute SHA256 for every file listed in Dataset v1's checksum manifests and the
    trajectory manifest's sha256 column; return a list of problem descriptions (empty if clean).

    Read-only: never writes to any Dataset v1 path.
    """
    import csv
    import json

    problems: List[str] = []

    checksum_manifests = [
        root / "benchmarks" / "point_ik" / "point_ik_checksum.json",
        root / "benchmarks" / "validation" / "validation_checksum.json",
    ]
    for manifest_path in checksum_manifests:
        if not manifest_path.is_file():
            problems.append(f"missing checksum manifest: {manifest_path}")
            continue
        with open(manifest_path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        for entry in manifest.get("files", []):
            file_path = root / entry["filename"]
            if not file_path.is_file():
                problems.append(f"missing v1 file: {file_path}")
                continue
            actual = sha256_file(file_path)
            if actual != entry["sha256"]:
                problems.append(
                    f"v1 file hash mismatch: {entry['filename']} "
                    f"(expected {entry['sha256']}, got {actual})"
                )

    trajectory_manifest = root / "trajectories" / "trajectory_manifest.csv"
    if not trajectory_manifest.is_file():
        problems.append(f"missing trajectory manifest: {trajectory_manifest}")
    else:
        with open(trajectory_manifest, "r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                file_path = root / row["file_path"]
                expected = row["sha256"]
                if not file_path.is_file():
                    problems.append(f"missing v1 trajectory file: {file_path}")
                    continue
                actual = sha256_file(file_path)
                if actual != expected:
                    problems.append(
                        f"v1 trajectory hash mismatch: {row['file_path']} "
                        f"(expected {expected}, got {actual})"
                    )

    return problems


def _check_dataset_v1_immutability(report: _Report, root: Path) -> None:
    try:
        problems = _verify_dataset_v1_immutability(root)
    except Exception as exc:  # noqa: BLE001 - surface any unexpected read failure as an audit fail
        report.record("dataset_v1_immutability", "fail", f"could not verify: {exc}")
        return
    if problems:
        report.record("dataset_v1_immutability", "fail", "; ".join(problems))
    else:
        report.record(
            "dataset_v1_immutability", "pass", "all checksum-manifest-listed v1 files unchanged"
        )


def _check_dataset_v2_public_root(report: _Report, dataset_v2_root: Optional[Path]) -> None:
    if dataset_v2_root is None:
        report.record("dataset_v2_public_root", "skip", "no --dataset-v2-root supplied")
        return

    from dataset_v2.locator import require_dataset_v2_root
    from utils.exceptions import ModelConfigurationError

    try:
        paths = require_dataset_v2_root(dataset_v2_root)
    except ModelConfigurationError as exc:
        report.record("dataset_v2_public_root", "fail", str(exc))
        return

    if not paths.checksum_manifest_file.is_file():
        report.record(
            "dataset_v2_public_root",
            "fail",
            f"checksum manifest not found: {paths.checksum_manifest_file}",
        )
        return

    report.record(
        "dataset_v2_public_root",
        "pass",
        f"manifest + checksum manifest present at {paths.root} "
        "(existence only; no sibling scan, no frozen_test content read)",
    )


def _check_frozen_denied_by_default(report: _Report) -> None:
    if is_split_access_allowed("frozen_test"):
        report.record(
            "frozen_access_denied_by_default", "fail", "frozen_test was NOT denied by default"
        )
        return
    report.record(
        "frozen_access_denied_by_default", "pass", "frozen_test denied without explicit override"
    )


def _check_dependencies(report: _Report) -> None:
    for module_name in _REQUIRED_DEPENDENCIES:
        try:
            __import__(module_name)
        except ImportError:
            report.record(f"dependency_{module_name}", "fail", "missing (required for Phase 1)")
        else:
            report.record(f"dependency_{module_name}", "pass", "available")

    for module_name in _OPTIONAL_DEPENDENCIES:
        try:
            __import__(module_name)
        except ImportError:
            report.record(
                f"dependency_{module_name}", "warn", "missing (optional, not required in Phase 1)"
            )
        else:
            report.record(
                f"dependency_{module_name}", "pass", "available (optional, not required in Phase 1)"
            )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-v2-root",
        type=str,
        default=None,
        help=(
            "Optional explicit Dataset v2 public root. Only its manifest/checksum-manifest "
            "*existence* is checked -- never scanned beyond that, never a sibling directory, "
            "never frozen_test content."
        ),
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    dataset_v2_root: Optional[Path] = None
    if args.dataset_v2_root is not None:
        candidate_root = Path(args.dataset_v2_root)
        if not candidate_root.is_dir():
            print(
                f"usage error: --dataset-v2-root does not exist or is not a directory: "
                f"{candidate_root}",
                file=sys.stderr,
            )
            return 2
        dataset_v2_root = candidate_root

    root = repo_root()
    report = _Report()

    _check_repo_root_and_git_state(report, root)
    _check_pdf_reference(report, root)
    _check_srpdik_configs(report)
    _check_dls_lock(report)
    _check_dataset_v1_immutability(report, root)
    _check_dataset_v2_public_root(report, dataset_v2_root)
    _check_frozen_denied_by_default(report)
    _check_dependencies(report)

    report.print_all()

    if report.has_failure():
        print("\n[run_srpdik_audit] FAIL", file=sys.stderr)
        return 1

    print("\n[run_srpdik_audit] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
