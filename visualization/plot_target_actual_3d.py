"""3D Cartesian target-vs-actual trajectory plot for the Dataset v2 DLS baseline.

Plots two curves in one 3D Matplotlib figure:

- **Target trajectory**: the requested Cartesian pose sequence (``target_position_*``
  columns of a Tier 2 evaluation run's ``waypoint_results.csv``).
- **Actual trajectory**: the Cartesian pose the warm-start DLS solver actually reached
  at each waypoint (``actual_position_*`` columns, same file, same rows).

Both curves come from the *same* real evaluation run
(``development/cand_D_pure_dls`` -- the pre-registered candidate selected and locked
by ``evaluation_v2/selection.py``, see ``docs/V2_IMPLEMENTATION_LOG.md`` Phase 8A/8B).
Nothing is synthesized: no target point is invented and no actual point is a
recomputed/idealized value -- both are read verbatim from the evaluation CSV.

Which trajectory/trial is plotted is controlled by ``--level {easy,medium,hard}``,
resolved through ``trajectory_plot_presets.json`` (see that file's ``selection_rule``
for exactly how each preset's trajectory/trial was picked from the real dataset
manifests -- first match by metadata filter, sorted by id, never a best-case pick).
Use ``--preset <shape>-<orientation_mode>-<difficulty>`` style custom filters via
``--source/--shape/--orientation-mode/--challenge-family/--difficulty`` if you want a
combination outside the three shipped presets.

Usage (from repo root)::

    python visualization/plot_target_actual_3d.py --level easy
    python visualization/plot_target_actual_3d.py --level medium
    python visualization/plot_target_actual_3d.py --level hard
    python visualization/plot_target_actual_3d.py --level hard --output hard.png --no-show
    python visualization/plot_target_actual_3d.py --list-presets
    python visualization/plot_target_actual_3d.py --source core --shape circle \\
        --orientation-mode fixed --difficulty hard
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_PRESETS_PATH = SCRIPT_DIR / "trajectory_plot_presets.json"

# Dataset v2 lives *outside* the repo (external data roots, never committed --
# see docs/CHATGPT_DLS_CURRENT_STATE_BRIEF.md section 1). These are only the
# auto-detection defaults; --dataset-root / --eval-root always win.
_SIBLING_SEARCH_DIRS = [REPO_ROOT.parent]
_DATASET_ROOT_CANDIDATE_NAMES = ["mpdik_kassow_v2_work"]
_EVAL_ROOT_CANDIDATE_NAMES = ["mpdik_kassow_v2_eval_devval"]

# dataviz skill categorical palette, light-mode slots 1 (blue) and 2 (orange):
# colorblind-safe adjacent pair (worst-case CVD delta-E 9.1, see
# visualization/README_TARGET_ACTUAL_3D.md).
COLOR_TARGET = "#2a78d6"
COLOR_ACTUAL = "#eb6834"
COLOR_START = "#1baf7a"
COLOR_END = "#e34948"
COLOR_MUTED_TEXT = "#52514e"


class PresetError(RuntimeError):
    """Raised when a preset cannot be resolved or cross-checked against real data."""


@dataclass(frozen=True)
class ResolvedSelection:
    level: str
    description: str
    trajectory_id: str
    trial_id: str
    split: str
    eval_candidate_id: str
    method: str
    filters: dict
    resolved: dict


def _first_existing(base_dirs: list[Path], names: list[str]) -> Optional[Path]:
    for base in base_dirs:
        for name in names:
            candidate = base / name
            if candidate.is_dir():
                return candidate.resolve()
    return None


def resolve_dataset_v2_root(explicit: Optional[str]) -> Path:
    if explicit is not None:
        root = Path(explicit).expanduser()
        if not root.is_absolute():
            root = Path.cwd() / root
        root = root.resolve()
        if not root.is_dir():
            raise PresetError(f"--dataset-root does not exist or is not a directory: {root}")
        return root

    found = _first_existing(_SIBLING_SEARCH_DIRS, _DATASET_ROOT_CANDIDATE_NAMES)
    if found is None:
        tried = ", ".join(str(d / n) for d in _SIBLING_SEARCH_DIRS for n in _DATASET_ROOT_CANDIDATE_NAMES)
        raise PresetError(
            "Could not auto-detect the Dataset v2 root. Tried: "
            f"{tried}. Pass --dataset-root explicitly."
        )
    return found


def resolve_eval_root(explicit: Optional[str]) -> Path:
    if explicit is not None:
        root = Path(explicit).expanduser()
        if not root.is_absolute():
            root = Path.cwd() / root
        root = root.resolve()
        if not root.is_dir():
            raise PresetError(f"--eval-root does not exist or is not a directory: {root}")
        return root

    found = _first_existing(_SIBLING_SEARCH_DIRS, _EVAL_ROOT_CANDIDATE_NAMES)
    if found is None:
        tried = ", ".join(str(d / n) for d in _SIBLING_SEARCH_DIRS for n in _EVAL_ROOT_CANDIDATE_NAMES)
        raise PresetError(
            "Could not auto-detect the Dataset v2 evaluation root. Tried: "
            f"{tried}. Pass --eval-root explicitly."
        )
    return found


def load_presets(presets_path: Path) -> dict:
    if not presets_path.is_file():
        raise PresetError(f"presets file not found: {presets_path}")
    with presets_path.open(encoding="utf-8") as f:
        return json.load(f)


def _read_csv_rows(path: Path) -> list[dict]:
    if not path.is_file():
        raise PresetError(f"expected manifest/result file not found: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def select_trajectory_id(
    dataset_root: Path,
    source: str,
    shape: Optional[str],
    orientation_mode: Optional[str],
    challenge_family: Optional[str],
) -> str:
    """Re-derive the selection independently from the real manifests (see
    trajectory_plot_presets.json::selection_rule): filter by metadata only,
    sort by trajectory_id, take the first."""
    if source == "core":
        manifest_path = dataset_root / "trajectories" / "core_trajectory_manifest.csv"
        rows = _read_csv_rows(manifest_path)
        matches = [
            row
            for row in rows
            if row["shape"] == shape and row["orientation_mode"] == orientation_mode
        ]
        criteria = f"shape={shape!r}, orientation_mode={orientation_mode!r}"
    elif source == "challenge":
        manifest_path = dataset_root / "trajectories" / "challenge_trajectory_manifest.csv"
        rows = _read_csv_rows(manifest_path)
        matches = [row for row in rows if row["challenge_family"] == challenge_family]
        criteria = f"challenge_family={challenge_family!r}"
    else:
        raise PresetError(f"unknown source {source!r} (expected 'core' or 'challenge')")

    if not matches:
        raise PresetError(
            f"no trajectory in {manifest_path} matches {criteria}; "
            "the dataset may have been regenerated -- update trajectory_plot_presets.json"
        )
    matches.sort(key=lambda row: row["trajectory_id"])
    return matches[0]["trajectory_id"]


def select_trial_id(dataset_root: Path, trajectory_id: str, difficulty: str) -> str:
    manifest_path = dataset_root / "trials" / "trial_manifest.csv"
    rows = _read_csv_rows(manifest_path)
    matches = [
        row
        for row in rows
        if row["trajectory_id"] == trajectory_id and row["difficulty"] == difficulty
    ]
    if not matches:
        raise PresetError(
            f"no trial in {manifest_path} matches trajectory_id={trajectory_id!r}, "
            f"difficulty={difficulty!r}"
        )
    matches.sort(key=lambda row: row["trial_id"])
    return matches[0]["trial_id"]


def verify_selection(dataset_root: Path, selection: ResolvedSelection) -> None:
    """Cross-check the resolved (trajectory_id, trial_id) against the live manifests.
    Raises PresetError loudly on any mismatch rather than silently trusting the
    JSON cache."""
    filters = selection.filters
    live_trajectory_id = select_trajectory_id(
        dataset_root,
        source=filters["source"],
        shape=filters.get("shape"),
        orientation_mode=filters.get("orientation_mode"),
        challenge_family=filters.get("challenge_family"),
    )
    if live_trajectory_id != selection.trajectory_id:
        raise PresetError(
            f"preset '{selection.level}' is stale: live selection rule now picks "
            f"trajectory_id={live_trajectory_id!r}, but the preset recorded "
            f"{selection.trajectory_id!r}. Regenerate trajectory_plot_presets.json."
        )

    live_trial_id = select_trial_id(dataset_root, live_trajectory_id, filters["difficulty"])
    if live_trial_id != selection.trial_id:
        raise PresetError(
            f"preset '{selection.level}' is stale: live selection rule now picks "
            f"trial_id={live_trial_id!r}, but the preset recorded {selection.trial_id!r}. "
            "Regenerate trajectory_plot_presets.json."
        )


def resolve_selection_from_level(presets: dict, level: str) -> ResolvedSelection:
    try:
        preset = presets["presets"][level]
    except KeyError as exc:
        available = ", ".join(sorted(presets.get("presets", {})))
        raise PresetError(f"unknown --level {level!r}; available presets: {available}") from exc

    resolved = preset["resolved"]
    return ResolvedSelection(
        level=preset["level"],
        description=preset["description"],
        trajectory_id=resolved["trajectory_id"],
        trial_id=resolved["trial_id"],
        split=resolved["split"],
        eval_candidate_id=resolved["eval_candidate_id"],
        method=resolved["method"],
        filters=preset["filters"],
        resolved=resolved,
    )


def resolve_selection_from_filters(
    dataset_root: Path,
    *,
    source: str,
    shape: Optional[str],
    orientation_mode: Optional[str],
    challenge_family: Optional[str],
    difficulty: str,
    split: str,
    eval_candidate_id: str,
    method: str,
) -> ResolvedSelection:
    trajectory_id = select_trajectory_id(dataset_root, source, shape, orientation_mode, challenge_family)
    trial_id = select_trial_id(dataset_root, trajectory_id, difficulty)
    filters = {"source": source, "difficulty": difficulty}
    if source == "core":
        filters["shape"] = shape
        filters["orientation_mode"] = orientation_mode
    else:
        filters["challenge_family"] = challenge_family
    resolved = {
        "trajectory_id": trajectory_id,
        "trial_id": trial_id,
        "split": split,
        "eval_candidate_id": eval_candidate_id,
        "method": method,
    }
    return ResolvedSelection(
        level="custom",
        description=f"Custom filter: {filters}",
        trajectory_id=trajectory_id,
        trial_id=trial_id,
        split=split,
        eval_candidate_id=eval_candidate_id,
        method=method,
        filters=filters,
        resolved=resolved,
    )


def load_waypoints(eval_root: Path, selection: ResolvedSelection) -> list[dict]:
    waypoint_results_path = (
        eval_root
        / selection.split
        / selection.eval_candidate_id
        / "tier2_sequential_dls"
        / "waypoint_results.csv"
    )
    rows = _read_csv_rows(waypoint_results_path)
    matches = [
        row
        for row in rows
        if row["trial_id"] == selection.trial_id and row["method"] == selection.method
    ]
    if not matches:
        raise PresetError(
            f"no waypoint rows in {waypoint_results_path} match trial_id="
            f"{selection.trial_id!r}, method={selection.method!r}"
        )
    matches.sort(key=lambda row: int(row["waypoint_id"]))
    return matches


def _floats(rows: list[dict], *cols: str):
    return [[float(row[c]) for c in cols] for row in rows]


def make_plot(selection: ResolvedSelection, rows: list[dict], *, elev: float, azim: float):
    import matplotlib.pyplot as plt

    target = _floats(rows, "target_position_x", "target_position_y", "target_position_z")
    actual = _floats(rows, "actual_position_x", "actual_position_y", "actual_position_z")
    tx, ty, tz = zip(*target)
    ax_, ay, az = zip(*actual)
    pos_err = [float(row["position_error_m"]) for row in rows]

    fig = plt.figure(figsize=(9, 7.5))
    ax = fig.add_subplot(111, projection="3d")

    ax.plot(tx, ty, tz, color=COLOR_TARGET, linewidth=2.0, linestyle="-", label="Target trajectory", zorder=3)
    ax.plot(ax_, ay, az, color=COLOR_ACTUAL, linewidth=2.0, linestyle="--", label="Actual trajectory (warm-start DLS)", zorder=4)

    ax.scatter([tx[0]], [ty[0]], [tz[0]], color=COLOR_START, marker="o", s=60, label="Start", zorder=5)
    ax.scatter([tx[-1]], [ty[-1]], [tz[-1]], color=COLOR_END, marker="s", s=60, label="End (target)", zorder=5)
    ax.scatter([ax_[-1]], [ay[-1]], [az[-1]], color=COLOR_END, marker="^", s=60, label="End (actual)", zorder=5)

    # Equal-aspect cube so geometry isn't visually distorted.
    all_x, all_y, all_z = tx + ax_, ty + ay, tz + az
    x_mid, y_mid, z_mid = (max(all_x) + min(all_x)) / 2, (max(all_y) + min(all_y)) / 2, (max(all_z) + min(all_z)) / 2
    half_range = max(max(all_x) - min(all_x), max(all_y) - min(all_y), max(all_z) - min(all_z)) / 2
    half_range = max(half_range, 1e-4) * 1.15
    ax.set_xlim(x_mid - half_range, x_mid + half_range)
    ax.set_ylim(y_mid - half_range, y_mid + half_range)
    ax.set_zlim(z_mid - half_range, z_mid + half_range)
    try:
        ax.set_box_aspect((1, 1, 1))
    except AttributeError:
        pass

    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Z (m)")
    ax.view_init(elev=elev, azim=azim)

    max_err = max(pos_err)
    mean_err = sum(pos_err) / len(pos_err)
    title = (
        f"Dataset v2 -- {selection.level.upper()} preset\n"
        f"{selection.trial_id}  |  split={selection.split}  |  method={selection.method}\n"
        f"mean pos. error = {mean_err * 1000:.2f} mm, max = {max_err * 1000:.2f} mm "
        f"(n={len(rows)} waypoints)"
    )
    ax.set_title(title, fontsize=10, color="#0b0b0b")
    ax.legend(loc="upper left", fontsize=8)
    fig.text(0.01, 0.01, selection.description, fontsize=7, color=COLOR_MUTED_TEXT)
    fig.tight_layout()
    return fig


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--level", choices=["easy", "medium", "hard"], help="Use a shipped preset from trajectory_plot_presets.json.")
    parser.add_argument("--presets", default=str(DEFAULT_PRESETS_PATH), help="Path to the presets JSON file.")
    parser.add_argument("--list-presets", action="store_true", help="Print available presets and exit.")

    custom = parser.add_argument_group("custom selection (used when --level is omitted)")
    custom.add_argument("--source", choices=["core", "challenge"], help="Trajectory source.")
    custom.add_argument("--shape", choices=["line", "circle", "figure8", "helix", "free_form"], help="Core trajectory shape.")
    custom.add_argument("--orientation-mode", choices=["fixed", "variable"], help="Core trajectory orientation mode.")
    custom.add_argument(
        "--challenge-family",
        choices=[
            "smooth_random",
            "mixed_curvature",
            "non_planar",
            "large_orientation",
            "near_limit_region",
            "near_singular_region",
        ],
        help="Random-challenge family.",
    )
    custom.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="easy", help="Trial initial-state difficulty class.")
    custom.add_argument("--split", default="development", help="Split to read the evaluation run from (must match --eval-root layout).")
    custom.add_argument("--eval-candidate-id", default="cand_D_pure_dls", help="Evaluation candidate id (subfolder under <eval-root>/<split>/).")
    custom.add_argument("--method", choices=["warm_start", "cold_start"], default="warm_start", help="'warm_start' = warm-start DLS.")

    parser.add_argument("--dataset-root", default=None, help="Dataset v2 root (default: auto-detect a sibling 'mpdik_kassow_v2_work' directory).")
    parser.add_argument("--eval-root", default=None, help="Dataset v2 evaluation output root (default: auto-detect a sibling 'mpdik_kassow_v2_eval_devval' directory).")
    parser.add_argument("--no-verify", action="store_true", help="Skip re-checking the preset's ids against the live manifests.")
    parser.add_argument("--elev", type=float, default=22.0, help="3D camera elevation angle (degrees).")
    parser.add_argument("--azim", type=float, default=-60.0, help="3D camera azimuth angle (degrees).")
    parser.add_argument("--output", default=None, help="Save the figure to this path (e.g. out.png) instead of/in addition to showing it.")
    parser.add_argument("--dpi", type=int, default=150, help="DPI used when saving --output.")
    parser.add_argument("--no-show", action="store_true", help="Do not open an interactive window (useful for CI/headless runs).")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.no_show:
        # Headless/CI-friendly backend; must be set before pyplot is imported anywhere.
        import matplotlib

        matplotlib.use("Agg")

    presets_path = Path(args.presets)

    if args.list_presets:
        try:
            presets = load_presets(presets_path)
        except PresetError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"Presets file: {presets_path}")
        for name, preset in presets.get("presets", {}).items():
            print(f"  {name}: {preset['description']}")
            print(f"    trajectory_id={preset['resolved']['trajectory_id']}")
            print(f"    trial_id={preset['resolved']['trial_id']}")
        return 0

    try:
        dataset_root = resolve_dataset_v2_root(args.dataset_root)
        eval_root = resolve_eval_root(args.eval_root)

        if args.level:
            presets = load_presets(presets_path)
            selection = resolve_selection_from_level(presets, args.level)
            if not args.no_verify:
                verify_selection(dataset_root, selection)
        else:
            if not args.source:
                raise PresetError("either --level or --source must be given (see --help).")
            if args.source == "core" and not (args.shape and args.orientation_mode):
                raise PresetError("--source core requires --shape and --orientation-mode.")
            if args.source == "challenge" and not args.challenge_family:
                raise PresetError("--source challenge requires --challenge-family.")
            selection = resolve_selection_from_filters(
                dataset_root,
                source=args.source,
                shape=args.shape,
                orientation_mode=args.orientation_mode,
                challenge_family=args.challenge_family,
                difficulty=args.difficulty,
                split=args.split,
                eval_candidate_id=args.eval_candidate_id,
                method=args.method,
            )

        print(f"Dataset v2 root: {dataset_root}")
        print(f"Evaluation root: {eval_root}")
        print(f"Selected trajectory_id: {selection.trajectory_id}")
        print(f"Selected trial_id:      {selection.trial_id}")
        print(f"Split / candidate / method: {selection.split} / {selection.eval_candidate_id} / {selection.method}")

        rows = load_waypoints(eval_root, selection)
    except PresetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    fig = make_plot(selection, rows, elev=args.elev, azim=args.azim)

    if args.output:
        fig.savefig(args.output, dpi=args.dpi)
        print(f"Saved figure to {args.output}")

    if not args.no_show:
        import matplotlib.pyplot as plt

        plt.show()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
