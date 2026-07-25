"""Assemble the public Dataset v2.0.0 release: a packaging step over data that is ALREADY
public and already checksum-verified (the development/validation public root, the frozen-only
public root, and the three completed evaluation runs' non-protected summary outputs). This module
copies and concatenates -- it never reads the dataset root's protected arrays and never reads
anything under a protected-validation root.

Release layout (under an explicit release root):
    VERSION                          -- "2.0.0"
    DATASET_MANIFEST.json            -- release-level manifest (counts, fingerprints, splits)
    configs/, schemas/                -- Dataset v2's OWN generation configs/schemas (not v1's)
    tier0_public/tier0_gate_results.json
    tier1_point_ik/{development,validation,frozen_test}.npz
    trials/{development,validation,frozen_test}.npz
    trajectories/{development,validation,frozen_test}/*.npz + per-split manifest
    trajectories/public_trajectory_manifest.csv   (combined, all splits)
    trial_manifest.csv                            (combined, all splits)
    evaluation_protocol.json                      (locked candidate + thresholds, no protected data)
    final_dls_summary.json                        (development vs validation vs frozen, not pooled)
    release_notes.md
    known_limitations.md
    CHECKSUM_MANIFEST.json                        (sha256 of every other file in the release)
"""

import csv
import json
import shutil
from pathlib import Path
from typing import Dict, List

from evaluation_v2 import fingerprints
from evaluation_v2.locator import public_eval_paths
from utils.file_checksum import sha256_file

RELEASE_VERSION = "2.0.0"
RELEASE_SPLITS = ("development", "validation", "frozen_test")


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")


def _copy_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def _split_root(dev_val_root: Path, frozen_root: Path, split: str) -> Path:
    return frozen_root if split == "frozen_test" else dev_val_root


def assemble_public_release(
    v2_work_root: Path,
    public_dev_val_root: Path,
    public_frozen_root: Path,
    release_root: Path,
    *,
    run_dirs: Dict[str, Path],
    lock_bundle: dict,
    final_dls_summary: dict,
    overwrite: bool = False,
) -> dict:
    v2_work_root = Path(v2_work_root)
    public_dev_val_root = Path(public_dev_val_root)
    public_frozen_root = Path(public_frozen_root)
    release_root = Path(release_root)

    if release_root.exists() and any(release_root.iterdir()) and not overwrite:
        raise FileExistsError(f"release root {release_root} already exists and is non-empty.")
    release_root.mkdir(parents=True, exist_ok=True)

    dev_val = public_eval_paths(public_dev_val_root, require_exists=True)
    frozen = public_eval_paths(public_frozen_root, require_exists=True)

    # ---- VERSION ----
    (release_root / "VERSION").write_text(RELEASE_VERSION + "\n", encoding="utf-8")

    # ---- configs / schemas: Dataset v2's OWN, never v1's ----
    _copy_tree(v2_work_root / "configs", release_root / "configs")
    _copy_tree(v2_work_root / "schemas", release_root / "schemas")

    # ---- Tier 1 point-IK ----
    (release_root / "tier1_point_ik").mkdir(parents=True, exist_ok=True)
    point_counts = {}
    for split in RELEASE_SPLITS:
        src_root = _split_root(dev_val, frozen, split)
        src = src_root.point_ik_split_file(split)
        dst = release_root / "tier1_point_ik" / f"{split}.npz"
        shutil.copy2(src, dst)
        from utils.npz_utils import load_npz
        point_counts[split] = int(load_npz(dst)["sample_id"].shape[0])

    # ---- Trials ----
    (release_root / "trials").mkdir(parents=True, exist_ok=True)
    trial_counts = {}
    trial_manifest_rows: List[dict] = []
    from utils.npz_utils import load_npz as _load
    for split in RELEASE_SPLITS:
        src_root = _split_root(dev_val, frozen, split)
        src = src_root.trials_split_file(split)
        dst = release_root / "trials" / f"{split}.npz"
        shutil.copy2(src, dst)
        arrays = _load(dst)
        trial_counts[split] = int(arrays["trial_id"].shape[0])
        for i in range(trial_counts[split]):
            trial_manifest_rows.append({
                "split": split,
                "trial_id": str(arrays["trial_id"][i]),
                "trajectory_id": str(arrays["trajectory_id"][i]),
                "trajectory_family": str(arrays["trajectory_family"][i]),
                "difficulty": str(arrays["difficulty"][i]),
            })
    trial_manifest_rows.sort(key=lambda r: (r["split"], r["trial_id"]))
    _write_manifest_csv(
        release_root / "trial_manifest.csv",
        ("split", "trial_id", "trajectory_id", "trajectory_family", "difficulty"),
        trial_manifest_rows,
    )

    # ---- Trajectories ----
    traj_root = release_root / "trajectories"
    traj_root.mkdir(parents=True, exist_ok=True)
    combined_rows: List[dict] = []
    traj_counts = {}
    columns = None
    for split in RELEASE_SPLITS:
        src_root = _split_root(dev_val, frozen, split)
        src_dir = src_root.trajectory_split_dir(split)
        dst_dir = traj_root / split
        _copy_tree(src_dir, dst_dir)
        manifest_csv = dst_dir / "public_manifest.csv"
        rows = []
        if manifest_csv.is_file():
            with open(manifest_csv, newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                columns = columns or reader.fieldnames
                rows = list(reader)
        combined_rows.extend(rows)
        traj_counts[split] = len(rows)
    combined_rows.sort(key=lambda r: (r.get("split", ""), r.get("trajectory_id", "")))
    _write_manifest_csv(traj_root / "public_trajectory_manifest.csv", list(columns or []), combined_rows)

    # ---- Tier 0 public data (structural gate results only, no per-sample data) ----
    tier0_dir = release_root / "tier0_public"
    tier0_dir.mkdir(parents=True, exist_ok=True)
    tier0_results = {}
    for split, run_dir in run_dirs.items():
        manifest_path = Path(run_dir) / "run_manifest.json"
        if manifest_path.is_file():
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
            tier0_results[split] = m["tiers"]["tier0"]
    _write_json(tier0_dir / "tier0_gate_results.json", tier0_results)

    # ---- Evaluation protocol (candidate + thresholds; no protected data) ----
    _write_json(release_root / "evaluation_protocol.json", {
        "selected_candidate_id": lock_bundle["selected_candidate_id"],
        "resolved_evaluation_config": lock_bundle["resolved_evaluation_config"],
        "lock_status": lock_bundle["lock_status"],
    })

    # ---- Final DLS summary ----
    _write_json(release_root / "final_dls_summary.json", final_dls_summary)

    # ---- DATASET_MANIFEST.json ----
    counts = {
        "point_ik_total": sum(point_counts.values()),
        "point_ik_by_split": point_counts,
        "trials_total": sum(trial_counts.values()),
        "trials_by_split": trial_counts,
        "trajectories_total": sum(traj_counts.values()),
        "trajectories_by_split": traj_counts,
        "canonical_poses_total": sum(traj_counts.values()) * 400,
    }
    dataset_manifest = {
        "version": RELEASE_VERSION,
        "name": "KR810_Tier0_Tier4_Dataset",
        "splits": list(RELEASE_SPLITS),
        "counts": counts,
        "frozen_core_revision": 4,
        "frozen_challenge_revision": 1,
        "frozen_trial_revision": 1,
        "scope": "Tier 0-4 kinematics only; no PPO/MPDIK/MAPPO/dynamics/actuators/controllers/torque/collision/real-robot content.",
        "protected_content_included": False,
    }
    _write_json(release_root / "DATASET_MANIFEST.json", dataset_manifest)

    return counts


def write_release_notes(path: Path, *, counts: dict, final_summary: dict) -> None:
    text = f"""# KR810 Tier0-Tier4 Dataset v2.0.0 -- Release Notes

## Contents
- {counts['point_ik_total']} Point-IK samples ({counts['point_ik_by_split']})
- {counts['trajectories_total']} trajectories, {counts['canonical_poses_total']} canonical waypoints
- {counts['trials_total']} trials ({counts['trials_by_split']})

## Selected DLS evaluation configuration
- Candidate: cand_D_pure_dls (adaptive damping, clip on, null-space joint-limit avoidance OFF)
- Solver convergence: 1 mm / 1 degree
- Reporting tiers: coarse 6 mm/5 deg, standard 3 mm/2 deg (primary), strict 1 mm/1 deg

## Baseline DLS results (development / validation / frozen_test)
See `final_dls_summary.json` for the full breakdown. Splits are reported side by side and are
never pooled into one number.

## Scope
Tier 0-4 kinematics only. Out of scope: PPO, MPDIK, MAPPO, dynamics, actuators, controllers,
torque control, collision, real-robot/TCP calibration, ISO certification claims.
"""
    path.write_text(text, encoding="utf-8")


def write_known_limitations(path: Path) -> None:
    text = """# Known Limitations

- No numeric quantitative-performance acceptance threshold is pre-registered for Phase 8A/8B;
  `quantitative_performance_acceptance_status` is `not_defined` by design (see project rules
  against inventing thresholds). Structural/isolation acceptance is the only pass/fail gate used.
- Acceleration feasibility (`acceleration_status`) is reported as
  `unavailable_no_locked_acceleration_limits`: no locked joint-acceleration limit exists for the
  KR810 in this dataset, so Tier 4 acceleration feasibility is descriptive-only, not a pass/fail
  metric.
- Warm-start and cold-start success rates are substantially lower than Point-IK success at the
  standard reporting tier; the dominant failure reasons are `stagnation` and `max_iterations`
  (never non-finite). These are exactly the failure modes intended to be handed to a future
  learned corrector (MPDIK/PPO), which is out of scope for this dataset release.
- This dataset and its DLS baseline cover Tier 0-4 kinematics only; no dynamics, actuator,
  controller, torque, or collision content is included.
"""
    path.write_text(text, encoding="utf-8")


def _write_manifest_csv(path: Path, columns, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


def write_checksum_manifest(release_root: Path) -> Path:
    release_root = Path(release_root)
    entries = []
    for path in sorted(p for p in release_root.rglob("*") if p.is_file() and p.name != "CHECKSUM_MANIFEST.json"):
        entries.append({"path": path.relative_to(release_root).as_posix(), "sha256": sha256_file(path)})
    out = release_root / "CHECKSUM_MANIFEST.json"
    _write_json(out, {"version": RELEASE_VERSION, "file_count": len(entries), "files": entries})
    return out
