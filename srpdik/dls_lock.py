"""Loads and verifies the locked pure-DLS snapshot (configs/srpdik/dls_locked.json).

Fail-closed: any missing file, hash mismatch, candidate-name mismatch, or resolved-parameter
drift raises DLSLockVerificationError immediately, with a diagnostic listing every problem
found (not just the first). This module never modifies kinematics/dls_solver.py,
evaluation_v2/candidate_configs.py, or any other locked DLS source/config file -- it only reads
and hashes them.
"""

import json
from typing import Dict

from srpdik.constants import DLS_LOCK_FILENAME, OFFICIAL_DLS_CANDIDATE_ID
from srpdik.exceptions import DLSLockVerificationError
from srpdik.paths import repo_root, srpdik_config_path
from utils.file_checksum import sha256_file

REQUIRED_LOCK_FIELDS = (
    "candidate_name",
    "immutable",
    "source_config_relative_path",
    "source_config_sha256",
    "source_code_files",
    "resolved_parameters",
    "pose_error_convention",
    "pose_error_frame",
    "jacobian_frame",
    "end_effector_site",
    "position_weight",
    "orientation_weight",
    "adaptive_damping_policy",
    "lambda_minimum",
    "lambda_maximum",
    "singularity_sigma_threshold",
    "maximum_iterations",
    "maximum_joint_step_rad",
    "clipping_policy",
    "joint_limit_policy",
    "stagnation_window",
    "minimum_relative_improvement",
    "coarse_standard_strict_thresholds",
    "snapshot_git_commit",
    "snapshot_timestamp_utc",
    "lock_format_version",
)


def _lock_path():
    return srpdik_config_path(DLS_LOCK_FILENAME)


def load_dls_lock() -> dict:
    """Load configs/srpdik/dls_locked.json.

    Fail-closed: raises DLSLockVerificationError if the file is missing, is not valid JSON, is
    missing a required field, or does not declare ``immutable: true``.
    """
    path = _lock_path()
    if not path.is_file():
        raise DLSLockVerificationError(f"DLS lock file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            lock = json.load(handle)
    except json.JSONDecodeError as exc:
        raise DLSLockVerificationError(f"DLS lock file is not valid JSON: {exc}") from exc

    if not isinstance(lock, dict):
        raise DLSLockVerificationError("DLS lock file must decode to a JSON object")

    missing = [field for field in REQUIRED_LOCK_FIELDS if field not in lock]
    if missing:
        raise DLSLockVerificationError(f"DLS lock file missing required field(s): {missing}")
    if lock.get("immutable") is not True:
        raise DLSLockVerificationError("DLS lock file must declare \"immutable\": true")
    return lock


def verify_candidate_name(lock: dict) -> None:
    """Fail-closed check that the locked candidate is the one official candidate."""
    name = lock.get("candidate_name")
    if name != OFFICIAL_DLS_CANDIDATE_ID:
        raise DLSLockVerificationError(
            f"locked candidate_name {name!r} does not match the official candidate "
            f"{OFFICIAL_DLS_CANDIDATE_ID!r}"
        )


def verify_source_hashes(lock: dict) -> Dict[str, str]:
    """Recompute SHA256 for every file in ``lock['source_code_files']`` and compare.

    Fail-closed: raises DLSLockVerificationError listing every missing/mismatched file (not
    just the first) if any recomputed hash differs from the lock, or a listed file is missing.
    Never modifies any hashed file. Returns the recomputed {relative_path: sha256} map on
    success.
    """
    root = repo_root()
    source_files = lock.get("source_code_files", {})
    if not source_files:
        raise DLSLockVerificationError("DLS lock has an empty source_code_files map")

    mismatches = []
    recomputed: Dict[str, str] = {}
    for rel_path, expected_hash in sorted(source_files.items()):
        path = root / rel_path
        if not path.is_file():
            mismatches.append(f"{rel_path}: file not found at {path}")
            continue
        actual_hash = sha256_file(path)
        recomputed[rel_path] = actual_hash
        if actual_hash != expected_hash:
            mismatches.append(f"{rel_path}: expected {expected_hash}, got {actual_hash}")

    source_config_rel = lock.get("source_config_relative_path")
    source_config_expected = lock.get("source_config_sha256")
    if source_config_rel not in source_files:
        mismatches.append(
            f"source_config_relative_path {source_config_rel!r} is not present in "
            "source_code_files"
        )
    elif recomputed.get(source_config_rel) != source_config_expected:
        mismatches.append(
            f"source_config_sha256 does not match the recomputed hash of {source_config_rel!r}"
        )

    if mismatches:
        raise DLSLockVerificationError(
            "DLS lock source hash verification failed:\n- " + "\n- ".join(mismatches)
        )
    return recomputed


def verify_resolved_parameters_match_live_source(lock: dict) -> None:
    """Cross-check ``lock['resolved_parameters']`` against a live, read-only read of
    ``evaluation_v2.candidate_configs.candidate_by_id(candidate_name).solver_config()``.

    This is independent of the source-hash check: it catches a transcription error in the lock
    file itself (source hashes could match while the recorded resolved_parameters were typed
    wrong). Only imports and calls the locked module; never modifies it.
    """
    from evaluation_v2.candidate_configs import candidate_by_id

    candidate_name = lock["candidate_name"]
    live_config = candidate_by_id(candidate_name).solver_config()
    locked_config = lock["resolved_parameters"]

    mismatches = {
        key: {"locked": locked_config.get(key), "live": live_config.get(key)}
        for key in set(locked_config) | set(live_config)
        if locked_config.get(key) != live_config.get(key)
    }
    if mismatches:
        raise DLSLockVerificationError(
            f"resolved_parameters in the lock do not match the live "
            f"candidate_by_id({candidate_name!r}).solver_config(): {mismatches}"
        )


def verify_dls_lock() -> dict:
    """Full fail-closed verification: schema, candidate name, source/config hashes, and a live
    resolved_parameters cross-check.

    Returns the verified lock dict on success. Raises DLSLockVerificationError with a clear
    diagnostic on any failure. Never modifies the lock file or any hashed/verified source file.
    """
    lock = load_dls_lock()
    verify_candidate_name(lock)
    verify_source_hashes(lock)
    verify_resolved_parameters_match_live_source(lock)
    return lock


def get_locked_candidate_config() -> dict:
    """Return the verified lock's ``resolved_parameters`` (the solver config values actually
    used by ``cand_D_pure_dls``).

    Raises DLSLockVerificationError (fail-closed) if verification fails; never returns an
    unverified config.
    """
    lock = verify_dls_lock()
    return dict(lock["resolved_parameters"])
