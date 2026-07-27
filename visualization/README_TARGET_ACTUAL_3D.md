# Target vs Actual 3D Trajectory Plot

`plot_target_actual_3d.py` draws a single 3D Matplotlib figure with two curves:

- **Target trajectory** — the requested Cartesian pose sequence.
- **Actual trajectory** — the Cartesian pose the DLS solver actually reached at
  each waypoint of the same trial.

Both curves are read verbatim from Dataset v2's own Tier 2 evaluation output
(`tier2_sequential_dls/waypoint_results.csv` of the `development/cand_D_pure_dls`
run — the pre-registered candidate that was selected and later locked for the
frozen-test run, see `docs/V2_IMPLEMENTATION_LOG.md` Phase 8A/8B). Nothing is
recomputed or idealized: `target_position_*`/`target_quaternion_*` and
`actual_position_*`/`actual_quaternion_*` are the same columns the evaluation
pipeline itself produced.

## Why the data lives outside the repo

Dataset v2 (generated data, ~500 files) and its evaluation runs are **external
data roots**, not part of this git repository (see `CLAUDE.md` and
`docs/CHATGPT_DLS_CURRENT_STATE_BRIEF.md` section 1). On this machine they are
sibling directories of the repo:

```
D:\data\hoang_anh\
  mpdik_kassow\                    <- this repo
  mpdik_kassow_v2_work\            <- Dataset v2 root (manifests, trajectories, trials)
  mpdik_kassow_v2_eval_devval\     <- Dataset v2 evaluation runs (development + validation)
```

The script auto-detects both by looking for those two sibling directory names
next to the repo root. If your layout differs, pass `--dataset-root` and
`--eval-root` explicitly (or set them once and forget it — there is no
CWD-relative or hardcoded-absolute-path assumption baked into the script).

## Usage

```bash
python visualization/plot_target_actual_3d.py --level easy
python visualization/plot_target_actual_3d.py --level medium
python visualization/plot_target_actual_3d.py --level hard

# Save instead of / in addition to showing a window (useful headless):
python visualization/plot_target_actual_3d.py --level hard --output hard.png --no-show

# See what each preset resolves to without plotting:
python visualization/plot_target_actual_3d.py --list-presets

# Point at a non-default dataset/eval location:
python visualization/plot_target_actual_3d.py --level easy \
    --dataset-root D:\path\to\mpdik_kassow_v2_work \
    --eval-root D:\path\to\mpdik_kassow_v2_eval_devval

# Plot any other real combination instead of a shipped preset:
python visualization/plot_target_actual_3d.py --source core --shape circle \
    --orientation-mode fixed --difficulty hard
python visualization/plot_target_actual_3d.py --source challenge \
    --challenge-family near_singular_region --difficulty medium
```

Camera angle (`--elev`/`--azim`), figure DPI (`--dpi` used with `--output`), and
skipping the live re-verification of a preset (`--no-verify`, faster but trusts
the JSON cache) are also available — see `--help` for the full list.

## The three presets

| Level  | Source    | Shape / family | Orientation mode | Difficulty | Method          |
|--------|-----------|-----------------|-------------------|------------|-----------------|
| easy   | core      | line            | fixed             | easy       | warm-start DLS  |
| medium | core      | helix           | variable          | medium     | warm-start DLS  |
| hard   | challenge | non_planar      | (n/a, per family) | hard       | warm-start DLS  |

Resolved identifiers (from the real Dataset v2 manifests, 2026-07-27 run):

| Level  | trajectory_id                                | trial_id                                                   | split       |
|--------|-----------------------------------------------|--------------------------------------------------------------|-------------|
| easy   | `core_line_fixed_anchor_near_limit_00`        | `core_line_fixed_anchor_near_limit_00_trial_easy`             | development |
| medium | `core_helix_variable_anchor_near_limit_00`    | `core_helix_variable_anchor_near_limit_00_trial_medium`        | development |
| hard   | `challenge_development_010`                   | `challenge_development_010_trial_hard`                         | development |

All three happen to land on the **development** split and the
**cand_D_pure_dls** evaluation candidate — that is a consequence of the
selection rule below, not something hardcoded in advance. `frozen_test` is
never touched here (the frozen-test protocol in `specs/DLS_DATASET_V2_SPEC.md`
section K reserves it for locked-config runs, not exploratory tooling).

### Selection rule (exactly what was done, no cherry-picking)

For each preset:

1. Filter `trajectories/core_trajectory_manifest.csv` (source `core`) or
   `trajectories/challenge_trajectory_manifest.csv` (source `challenge`) by
   metadata only — `shape` + `orientation_mode`, or `challenge_family`. No
   outcome/error/success column is ever consulted at this step.
2. Sort the surviving rows by `trajectory_id` (lexical ascending) and take the
   first.
3. Filter `trials/trial_manifest.csv` to `trial_id ==
   "<trajectory_id>_trial_<difficulty>"` (there are exactly three trials per
   trajectory — `easy`/`medium`/`hard` — by construction, spec section J).
4. Load that `trial_id`'s 400 waypoint rows from
   `<eval_root>/<split>/cand_D_pure_dls/tier2_sequential_dls/waypoint_results.csv`,
   `method == "warm_start"`, sorted by `waypoint_id`.

The resolved ids are cached in `trajectory_plot_presets.json` (see its own
`selection_rule` field for the same steps in machine-readable form, plus
`generated_from` provenance). Every run of `--level ...` **re-derives the
selection from the live manifests and asserts it still matches the cached
ids** (skip with `--no-verify`) — if the dataset is regenerated and the
selection would change, the script fails loudly instead of silently plotting
a stale trajectory:

```
error: preset 'easy' is stale: live selection rule now picks trajectory_id=...,
but the preset recorded '...'. Regenerate trajectory_plot_presets.json.
```

To regenerate the presets after a real dataset change, rerun the same manifest
queries used to build `trajectory_plot_presets.json` (see git history of that
file, or use `--source/--shape/--orientation-mode/--challenge-family
/--difficulty` to reproduce any one preset's selection ad hoc) and update the
`resolved` blocks.

## What the plot shows

- Solid blue line — target trajectory.
- Dashed orange line — actual (warm-start DLS) trajectory.
- Green circle — trial start. Red square — target end. Red triangle — actual
  end.
- Title reports the trial id, split, method, and the mean/max Cartesian
  position error actually measured over the 400 waypoints (not a cherry-picked
  number — it is `mean`/`max` of the same `position_error_m` column the
  evaluation pipeline wrote).
- Equal-aspect 3D axes (a cube, not a distorted box) so path geometry is not
  visually misleading.

Colors are the `dataviz` skill's default categorical palette (slots 1/2: blue
`#2a78d6` target, orange `#eb6834` actual) — validated colorblind-safe adjacent
pair, plus a redundant solid/dashed line-style encoding so the two curves are
distinguishable without relying on color alone.

Because these are real DLS baseline results (not synthetic demo data), some
plots show large excursions — e.g. the `easy` preset's trial has a ~48 cm
stagnation spike near the start of its line trajectory. That is a genuine,
already-documented DLS weakness (`docs/CHATGPT_DLS_CURRENT_STATE_BRIEF.md`
section 10: "stagnation dominates" / "heavy error tail"), not a plotting bug —
the selection rule never looks at error magnitude when picking which
trajectory/trial to show.

## Requirements

`matplotlib` (already a project dependency). No dataset-v2 Python package
import is required — the script only reads CSV/JSON files directly, so it
works even from a plain `python` outside the repo's `.venv`.
