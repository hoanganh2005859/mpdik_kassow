# DLS Target–Actual Plot Diagnosis

> Audit-only. No generator/evaluator/solver code was executed this turn other than reading
> existing CSV/manifest files. No dataset, evaluation, or training was regenerated. No code was
> modified.

`docs/srpdik/HANDOFF.md` does not exist in this repo (checked, not found) — not used as input.

## 1. Root cause (proven)

The "actual" curve looking very far from "target" is **not a plotting/data bug**. It is a
**genuine, reproducible warm-start DLS solver failure**: at the specific waypoints where the plot
looks bad, `converged=False` / `success_standard=False` with `failure_reason="stagnation"`, and
`actual_position_*` is the correctly-computed forward kinematics of the joint state the solver
actually stopped at (`FK(q_solution)`), which is simply far from the target because the solver
did not converge.

Contributing (secondary) issue, real but cosmetic: the plot script draws one continuous line
through all 400 waypoints regardless of `success_standard`, with no color/marker/NaN-break
distinguishing failed solves from converged ones (`visualization/plot_target_actual_3d.py:327-328`).
This makes a real solver-failure streak look, at a glance, like a data-integrity bug ("actual is
chaotic/wrong") rather than what it is (a correctly-recorded run of failed IK solves).

A secondary, unresolved observation worth flagging for further (not-this-turn) investigation:
`minimum_joint_limit_margin = 0.0` (exactly zero) at waypoint 0 in **all three** sampled trials,
and 100% of failures in all three trials have `failure_reason="stagnation"` (no
`joint_limit_failure`, `linear_solve_failure`, etc.). This pattern (margin exactly at the joint
boundary + stagnation-only failures) is consistent with the solver repeatedly hitting a
joint-limit clip and stalling, but confirming that mechanism would require an iteration-level
trace inside `dls_single_update`, which is out of scope for this diagnosis (see §7, "if not
enough evidence").

## 2. Evidence (file / symbol / line)

- `visualization/plot_target_actual_3d.py:288-308` (`load_waypoints`) — reads
  `waypoint_results.csv`, filters by exact `trial_id` **and** `method`, sorts by
  `int(row["waypoint_id"])` (numeric, not lexical — rules out checklist item C4).
- `visualization/plot_target_actual_3d.py:311-332` (`_floats`, `make_plot`) — plots
  `target_position_*` and `actual_position_*` columns directly, one line each, **no filtering or
  branching on `success_standard`/`converged`/`failure_reason`** — confirms checklist item C6
  (failed waypoints are joined by line with no visual distinction) is real.
- `evaluation_v2/trajectory_eval.py:92-125` (`evaluate_trajectory_trial`) — for every waypoint,
  regardless of `dls_result.success`, computes `fk = forward_kinematics(model_context, q_sol, ...)`
  and writes `actual_position_*` from **that FK**, where `q_sol = raw.dls_result.q_solution` is
  the final joint state the DLS attempt reached (converged or not). This rules out checklist items
  C1 (`p_initial` prepended), C2 (iteration trace plotted), C3 (401 vs 400 length mismatch — one
  row is written per input waypoint, 1:1), and C5/C9 (rows carry a single `trial_id`/`method`, no
  cross-trial mixing at write time).
- `algorithms/warm_start_dls.py:41-51,88-109` (`_recover_q_initial`, `run_warm_start_dls`) —
  confirms the warm-start recovery policy: the next waypoint's seed is the *just-attempted*
  `dls_result.q_solution` (finite by construction of `dls_single_update`), falling back to
  `last_successful_q` / `trial_q_initial` only if that were non-finite, which the module docstring
  states never happens in practice. Checklist item C7 (fallback to `q_initial` causing a visible
  jump) is therefore not the mechanism here — measured cross-waypoint jumps (below) come from the
  solver's own non-convergence, not from a fallback substitution.
- `mpdik_kassow_v2_work/trials/trial_manifest.csv` — `initial_position` (= `FK(q_initial)`),
  `first_target_position`, `initial_position_error_m` are precomputed at dataset-generation time
  and independently reproduce `distance(p_initial, target_0)` exactly (cross-checked below) —
  confirms the large `p_initial`↔`target_0` gaps are by design (easy/medium/hard `q_initial`
  classes, spec section J), consistent with the instruction not to treat that gap alone as a bug.
- `mpdik_kassow_v2_eval_devval/development/cand_D_pure_dls/tier2_sequential_dls/waypoint_results.csv`
  — the one file actually read for all quantitative findings below (filtered by exact `trial_id`,
  121 MB source, 800 matching rows per trial = 400 `warm_start` + 400 `cold_start`, no other trial
  ever appears once filtered by exact `trial_id`).

No solver/generator was re-run. The only code executed this turn was a read-only diagnostic script
(`csv.DictReader` + arithmetic) over the existing CSV, plus `grep` to slice out the three trials'
rows — never `dls_solver.py` / `warm_start_dls.py` / any pipeline.

## 3. Three-case comparison tables

All three from `development` split, `cand_D_pure_dls`, `tier2_sequential_dls/waypoint_results.csv`,
`method=warm_start`, `trajectory_id` == the single id shown (no mixing across trial/method/split
confirmed per case).

### Case A — easy (`core_line_fixed_anchor_near_limit_00_trial_easy`)

| field | value |
|---|---|
| trajectory_id / trial_id | `core_line_fixed_anchor_near_limit_00` / `core_line_fixed_anchor_near_limit_00_trial_easy` |
| difficulty / split / method | easy / development / warm_start |
| target_positions.shape / actual_positions.shape | (400,3) / (400,3) |
| waypoint index first/last, unique count | 0 / 399, 400 unique (numerically sorted, no lexical-sort artifact) |
| p_initial = FK(q_initial) | `[-0.2907, -0.1976, 0.9424]` |
| target_0 | `[0.2591, -0.4833, 0.6081]` |
| actual_0 = FK(q_solution[0]) | `[0.0655, -0.1639, 0.8189]` |
| distance(p_initial, target_0) | 0.7040 m |
| distance(actual_0, target_0) | 0.4289 m |
| success_standard[0] / failure_reason[0] | False / `stagnation` (17 iterations) |
| total success rate (400 wp, warm_start) | 398/400 = 99.50% |
| first failed waypoint | 0 |
| maximum failure streak | 2 |

### Case B — medium (`core_helix_variable_anchor_near_limit_00_trial_medium`)

| field | value |
|---|---|
| trajectory_id / trial_id | `core_helix_variable_anchor_near_limit_00` / `..._trial_medium` |
| difficulty / split / method | medium / development / warm_start |
| target_positions.shape / actual_positions.shape | (400,3) / (400,3) |
| waypoint index first/last, unique count | 0 / 399, 400 unique |
| p_initial = FK(q_initial) | `[0.3600, 0.0508, 0.9207]` |
| target_0 | `[0.2591, -0.4833, 0.6081]` |
| actual_0 = FK(q_solution[0]) | `[0.0051, -0.2036, 0.7733]` |
| distance(p_initial, target_0) | 0.6271 m |
| distance(actual_0, target_0) | 0.4124 m |
| success_standard[0] / failure_reason[0] | False / `stagnation` (17 iterations) |
| total success rate (400 wp, warm_start) | **71/400 = 17.75%** |
| first failed waypoint | 0 |
| maximum failure streak | **233** |

### Case C — hard (`challenge_development_010_trial_hard`)

| field | value |
|---|---|
| trajectory_id / trial_id | `challenge_development_010` / `..._trial_hard` |
| difficulty / split / method | hard / development / warm_start |
| target_positions.shape / actual_positions.shape | (400,3) / (400,3) |
| waypoint index first/last, unique count | 0 / 399, 400 unique |
| p_initial = FK(q_initial) | `[0.3905, 0.0015, 0.4990]` |
| target_0 | `[-0.1964, -0.9157, 0.0225]` |
| actual_0 = FK(q_solution[0]) | `[-0.1883, -0.8714, 0.0213]` |
| distance(p_initial, target_0) | 1.1886 m |
| distance(actual_0, target_0) | 0.0451 m |
| success_standard[0] / failure_reason[0] | False / `stagnation` (34 iterations) |
| total success rate (400 wp, warm_start) | **37/400 = 9.25%** |
| first failed waypoint | 0 |
| maximum failure streak | **194** |

**Note on Case C vs A/B:** despite having the largest `p_initial`↔`target_0` gap (1.19 m), Case C's
`actual_0` lands much closer to `target_0` (4.5 cm) than Case A/B — proof that "how far
`p_initial` is from `target_0`" and "how well DLS actually converges" are independent, exactly as
the task brief warned. The bad-looking chart is driven by the **233/400** and **194/400** failure
streaks (real non-convergence), not by the initial-pose gap.

## 4. What is a visualization issue

- `visualization/plot_target_actual_3d.py` connects every waypoint's `actual_position` with a
  solid line regardless of `success_standard`/`converged`, so a long real failure streak (e.g.
  Case B's 233 consecutive failed waypoints) renders as one continuous erratic orange curve
  indistinguishable, by eye, from corrupted data. This is checklist item C6, confirmed.
- The title/legend report `mean`/`max` position error but do not report success rate or failure
  streak, so a viewer has no way to tell "solver mostly failed here" from "plot is broken" without
  reading the CSV.
- Nothing else in the plotting path is wrong: waypoint sort is numeric (not lexical), shapes match
  1:1 at 400/400, single trial_id/trajectory_id/split/method per figure (re-verified live against
  manifests by `verify_selection`, `plot_target_actual_3d.py:199-224`), and `actual_position` is
  never `p_initial` or an iteration-history point.

## 5. What is a real DLS failure

- Waypoint 0 fails with `stagnation` in **all three** sampled trials (easy/medium/hard), not just
  the initially-far ones — i.e., this is not explained solely by the by-design
  easy/medium/hard `q_initial` gap.
- Case B and C show sustained non-convergence: 233/400 and 194/400 consecutive `stagnation`
  failures respectively — real solver behavior, correctly recorded, not a data artifact.
- 100% of failures in all three trials have `failure_reason == "stagnation"` (never
  `joint_limit_failure`, `linear_solve_failure`, `non_finite_*`, `max_iterations`) — a
  homogeneous failure mode.
- `minimum_joint_limit_margin == 0.0` (exact zero) at waypoint 0 in all three trials — flagged as
  an unresolved observation (§1), not yet root-caused to a specific line of `dls_single_update`
  within this turn's scope.

## 6. Files to change and minimal proposed diff (not applied)

1. `visualization/plot_target_actual_3d.py::make_plot` — split each of `target`/`actual` into
   contiguous runs by `success_standard` (or insert `NaN` at every waypoint where
   `success_standard == "False"`) before calling `ax.plot(...)` for the actual curve, and/or
   scatter failed waypoints with a distinct marker/color. Add success-rate and max-failure-streak
   to the title. This is the minimal change to stop real solver failures from reading as a
   plotting bug.
2. No change needed in `evaluation_v2/trajectory_eval.py` or `algorithms/warm_start_dls.py` for
   the plotting symptom — their output is correct per §2/§3.
3. Separate, not-this-turn investigation candidate if the stagnation rate itself is considered a
   problem: `kinematics/dls_solver.py::dls_single_update` (joint-limit clip interaction with the
   stagnation window, `_STAGNATION_WINDOW=5` / `_STAGNATION_MIN_RELATIVE_IMPROVEMENT=1e-3`) and
   `evaluation_v2/candidate_configs.py::cand_D_pure_dls` (null-space gain 0.0) — both plausible
   contributors to the `minimum_joint_limit_margin == 0.0` + 100%-stagnation pattern, but neither
   was traced at the iteration level this turn.

No code was modified in this turn.

## 7. Unknowns / next command if more evidence is needed

- UNKNOWN: exact iteration-by-iteration cause of `stagnation` at `minimum_joint_limit_margin=0.0`.
  Next command (read-only instrumentation, single trial, first few waypoints only — not a full
  solver re-run):
  ```
  python -c "
  import numpy as np
  from kinematics.model_loader import load_model_context
  from kinematics.dls_solver import solve_dls_until_converged
  from kinematics.quaternion_utils import quaternion_wxyz_to_matrix
  from evaluation_v2.candidate_configs import CandidateConfig
  # load q_initial for core_line_fixed_anchor_near_limit_00_trial_easy from
  # mpdik_kassow_v2_work/trials/development.npz, target_position[0]/target_quaternion[0]
  # from mpdik_kassow_v2_work/trajectories/development/core_line_fixed_anchor_near_limit_00.npz,
  # then call solve_dls_until_converged with a config that logs sigma_min/margin/step per
  # iteration (requires a temporary debug print inside dls_single_update — not done this turn).
  "
  ```
  This is diagnostic-only and would touch a single trial / a handful of waypoints, per the
  instructions; it was not run this turn because it requires a temporary code change (a debug
  print or return of per-iteration history) inside `dls_solver.py`, which is out of scope for an
  audit-only pass.
