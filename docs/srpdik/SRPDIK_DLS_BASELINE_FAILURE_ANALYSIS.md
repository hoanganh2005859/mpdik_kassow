# SR-PPO-DLS — Locked Pure-DLS Failure-Mode Analysis (Phase 1A)

Read-only analysis of the already-generated, already-evaluated `cand_D_pure_dls` Dataset v2
results. No solver/generator/evaluation code was executed this phase; no dataset v1/v2 file was
modified; `frozen_test` raw per-sample files were never opened (only the already-published
aggregate `final_dls_summary.json` and the frozen access ledger/report were read for the frozen
split — see §1).

## 1. Scope and data-use policy

This phase answers seven questions (where is DLS failing, what is the dominant failure mode,
which initial states are hard, how does waypoint 0 fail, at what data level does joint-limit
margin hit zero, which task groups SR-PPO-DLS training needs, and a preliminary sampling split)
purely by aggregating existing evaluation outputs. It does not implement `task_record`,
`training_stream`, a new baseline cache, observation/action/safety-filter code, reward, a Gym
environment, PPO, or a Kaggle notebook — all deferred to Phase 2+ per
`docs/srpdik/SRPDIK_IMPLEMENTATION_PLAN.md`.

**Data-access boundary actually observed:**

- Read: `KR810_Tier0_Tier4_Dataset_v2.0.0/final_dls_summary.json` (published frozen aggregate),
  `mpdik_kassow_v2_eval_frozen/frozen_access_ledger.json` / `frozen_access_report.json` (frozen
  governance record, not per-sample data), `mpdik_kassow_v2_eval_devval/{development,validation}
  /cand_D_pure_dls/{tier1_point_dls,tier2_sequential_dls,tier3_trajectory_tracking}/*.csv`
  (development/validation evaluation summaries — explicitly permitted by the governing prompt's
  §3 allowed-source list, and by `configs/srpdik/srpdik_data.json`'s
  `splits.validation.access = "requires_explicit_authorization"` policy, which this governing
  prompt's own §3 allow-list constitutes explicit authorization for read-only Phase 1A analysis),
  `resolved_config.json` (development run), `docs/CHATGPT_DLS_CURRENT_STATE_BRIEF.md`,
  `docs/srpdik/DLS_TRAJECTORY_PLOT_DIAGNOSIS.md` (pre-existing, cited for §9).
- **Not read**: any `frozen_test` per-sample CSV (`point_results.csv`, `point_failures.csv`,
  `waypoint_results.csv`, `trajectory_trial_summaries.csv` under
  `mpdik_kassow_v2_eval_frozen/frozen_test/cand_D_pure_dls/`), any protected evidence file
  (`trials/protected/*_evidence.npz`), any `q_reference`/`q_target_reference` array, any raw NPZ.
  Consequently every frozen-split row in this phase's tables is the **published aggregate only**
  — no per-difficulty-group, per-family, or per-trial breakdown exists for `frozen_test` in this
  analysis, by design.
- Point-IK per-sample initial joint-limit margin (`minimum_initial_limit_margin_normalized`) and
  per-waypoint initial `sigma_min`/margin are **not present** in the permitted evaluation-summary
  files (`point_results.csv` records only `initial_sigma_min` and a post-solve
  `minimum_joint_limit_margin`; `waypoint_results.csv` records only post-solve `sigma_min` /
  `minimum_joint_limit_margin`, no initial-state fields). These covariates exist only in
  generation-time reports/manifests in the dataset root, which were not opened this phase to keep
  the read scope to the named evaluation-summary sources. This is the direct cause of the
  `UNKNOWN_H1_VS_H2` conclusion in §6.

## 2. Official result sources

| # | result_type | split | method | file | key/table | public/protected | allowed |
|---|---|---|---|---|---|---|---|
| 1 | point-IK aggregate | development/validation/frozen_test | — | `KR810_Tier0_Tier4_Dataset_v2.0.0/final_dls_summary.json` | `{split}.point_ik.*` | public (released) | yes |
| 2 | point-IK per-sample | development, validation | — | `mpdik_kassow_v2_eval_devval/{split}/cand_D_pure_dls/tier1_point_dls/point_results.csv` | per-sample | public (dev/val eval output) | yes |
| 3 | point-IK per-group | development, validation | — | `.../tier1_point_dls/point_metrics.csv` | per-`difficulty_id` group | public | yes |
| 4 | point-IK failure detail | development, validation | — | `.../tier1_point_dls/point_failures.csv` | failed samples only | public | yes |
| 5 | trajectory per-waypoint | development, validation | warm_start, cold_start | `.../tier2_sequential_dls/waypoint_results.csv` | per-(trial,method,waypoint) | public | yes |
| 6 | trajectory per-trial | development, validation | warm_start, cold_start | `.../tier2_sequential_dls/trajectory_trial_summaries.csv` | per-(trial,method) | public | yes |
| 7 | warm-vs-cold paired | development, validation | both | `.../tier2_sequential_dls/warm_vs_cold.csv` | per-trial paired | public | not needed this phase |
| 8 | trajectory tracking | development, validation | warm_start, cold_start | `.../tier3_trajectory_tracking/trajectory_metrics.csv` | per-(trial,method), incl. `coverage_ratio` | public | yes |
| 9 | trajectory aggregate | frozen_test | warm_start, cold_start | `KR810_Tier0_Tier4_Dataset_v2.0.0/final_dls_summary.json` | `frozen_test.{warm_start,cold_start}.*` | public (released) | yes |
| 10 | resolved eval config | development | — | `.../development/cand_D_pure_dls/resolved_config.json` | candidate/solver params | public | yes |
| 11 | frozen access ledger | frozen_test | — | `mpdik_kassow_v2_eval_frozen/frozen_access_ledger.json` | `access_count`, events | governance record | yes |
| 12 | frozen access report | frozen_test | — | `mpdik_kassow_v2_eval_frozen/frozen_access_report.json` | `exact_workload`, `no_retune_confirmation` | governance record | yes |
| 13 | DLS lock snapshot | — | — | `configs/srpdik/dls_locked.json` | resolved solver parameters | in-repo | yes |
| 14 | prior plot diagnosis | development (3 sampled trials) | warm_start | `docs/srpdik/DLS_TRAJECTORY_PLOT_DIAGNOSIS.md` | qualitative + 3-trial table | in-repo doc | yes |
| — | **not read** | frozen_test | — | `mpdik_kassow_v2_eval_frozen/frozen_test/cand_D_pure_dls/tier{1,2}_*/*.csv` | per-sample/per-waypoint | raw frozen | **no** |

## 3. Success-rate reconciliation

The apparent discrepancy between "95.08%" (PDF p.1), "0.9508"/"0.951" (rounding in various
docs), and "95.1%" is **not a conflict** — all four strings denote the same underlying raw value,
`final_dls_summary.json::frozen_test.point_ik.success_standard = 0.9508333333333333`, at
different display precisions. `DECISIONS.md` #9 is resolved by this table:

| displayed_value | raw_value | split | method | threshold | aggregation | numerator | denominator | source |
|---|---|---|---|---|---|---|---|---|
| 95.08% | 0.9508333333333333 | frozen_test | point_ik | standard (3 mm / 2°) | micro (equal-weight per-sample mean over 3600 samples) | 3423 | 3600 | `final_dls_summary.json::frozen_test.point_ik.success_standard` |
| 0.9508 / 0.951 / 95.1% | 0.9508333333333333 | frozen_test | point_ik | standard | micro | 3423 | 3600 | same key — rounding only |
| 95.67% | 0.9566666666666667 | frozen_test | point_ik | coarse (6 mm / 5°) | micro | 3444 | 3600 | `final_dls_summary.json::frozen_test.point_ik.success_coarse` |
| 94.61% | 0.9461111111111111 | frozen_test | point_ik | strict (1 mm / 1°) | micro | 3406 | 3600 | `final_dls_summary.json::frozen_test.point_ik.success_strict` |
| 96.33% | 0.9633333333333334 | development | point_ik | standard | micro | 1156 | 1200 | `final_dls_summary.json::development.point_ik.success_standard`; cross-checked against `point_metrics.csv::group=overall,success_count_standard=1156` — exact match, no discrepancy |
| 96.25% | 0.9625 | validation | point_ik | standard | micro | 1155 | 1200 | `final_dls_summary.json::validation.point_ik.success_standard`; cross-checked against `point_metrics.csv::group=overall,success_count_standard=1155` — exact match |
| 54.93% | 0.5493095238095238 | frozen_test | trajectory warm_start | standard | macro-over-trials (= micro here, all trials have exactly 400 waypoints) | 46142 | 84000 | `final_dls_summary.json::frozen_test.warm_start.trial_macro_success_standard` |
| 32.92% | 0.32919047619047614 | frozen_test | trajectory cold_start | standard | macro (=micro) | 27652 | 84000 | `final_dls_summary.json::frozen_test.cold_start.trial_macro_success_standard` |
| 56.62% | 0.566154761904762 | development | trajectory warm_start | standard | macro (=micro) | 47557 | 84000 | `final_dls_summary.json::development.warm_start.trial_macro_success_standard` |
| 38.97% | 0.38971428571428574 | development | trajectory cold_start | standard | macro (=micro) | 32736 | 84000 | `final_dls_summary.json::development.cold_start.trial_macro_success_standard` |
| 69.05% | 0.6905357142857144 | validation | trajectory warm_start | standard | macro (=micro) | 58005 | 84000 | `final_dls_summary.json::validation.warm_start.trial_macro_success_standard` |
| 42.82% | 0.42823809523809525 | validation | trajectory cold_start | standard | macro (=micro) | 35972 | 84000 | `final_dls_summary.json::validation.cold_start.trial_macro_success_standard` |

**Official values locked for citation going forward:**

- Point-IK development standard success = **0.9633333333333334** (1156/1200).
- Point-IK validation standard success = **0.9625** (1155/1200).
- Point-IK frozen public standard success = **0.9508333333333333** (3423/3600) — this is "95.08%"/"0.951".
- Trajectory warm-start frozen standard success = **0.5493095238095238** (46142/84000).
- Trajectory cold-start frozen standard success = **0.32919047619047614** (27652/84000).

`DECISIONS.md` #9 is marked resolved (see updated `DECISIONS.md`).

## 4. Point-IK failure analysis

Full per-group table: `docs/srpdik/srpdik_dls_failure_mode_table.csv` (`result_type=point_ik`
rows). Groups follow `dataset_v2/config_templates.py::DIFFICULTY_GROUPS` (ids 0-5: `near_target`,
`medium_target`, `far_target`, `large_orientation_change`, `near_joint_limit`,
`near_singularity`), classified with `near_singularity` highest priority down to `near_target`
lowest (`CLASSIFICATION_PRIORITY_HIGHEST_FIRST`).

Development split (1200 samples, 200/group), standard-tier success by group:

| group | success_standard_rate | dominant failure_reason | median iterations | median initial σ_min |
|---|---:|---|---:|---:|
| near_target | 1.000 | — | 1 | 0.109 |
| medium_target | 1.000 | — | 2 | (not computed separately; comparable to near_target) |
| far_target | 0.985 | stagnation (3/3 failures) | 5 | 0.123 |
| large_orientation_change | **0.895** | stagnation (21/21 failures) | 13 | (not in table; high-orientation group) |
| near_joint_limit | 0.940 | mixed stagnation/max_iterations (9 stagnation, 7 max_iterations) | 26.3 | (near-limit by construction) |
| near_singularity | 0.960 | mixed (8 stagnation, 8 max_iterations) | 31.0 | low by construction (σ_min ≤ 0.03 threshold) |

Validation split shows the same ranking (`large_orientation_change` worst at 0.895, `near_target`/
`medium_target` perfect at 1.000), confirming the pattern is not split-specific.

**Key finding**: `large_orientation_change` is the single hardest point-IK group in both dev and
validation (10.5% standard failure rate, **100% of its failures are `stagnation`**, never
`max_iterations`/`joint_limit_failure`/`non_finite_*`) — this is a pure descent failure on
large-rotation targets, not a budget or numerical-safety problem. `near_joint_limit` and
`near_singularity` show a **mix** of `stagnation` and `max_iterations` failures, and much higher
iteration counts even when they succeed (median 26-31 vs. 1-5 for the easy groups) — this is the
`high_iteration_success` signal used in §9's training strata.

## 5. Trajectory failure analysis

Full per-(difficulty × method) and per-(source_type × method) tables:
`docs/srpdik/srpdik_dls_failure_mode_table.csv` (`result_type=trajectory` rows), built from
168,000 waypoint solves per split (210 trials × 400 waypoints × 2 methods).

| split | difficulty | method | success_standard_rate | stagnation_rate (of all waypoint solves) | median final margin | % final margin = 0 |
|---|---|---|---:|---:|---:|---:|
| development | easy | warm_start | 0.467 | (see CSV) | 0.0 | 0.53 |
| development | easy | cold_start | 0.437 | (see CSV) | 0.0 | 0.53 |
| development | medium | warm_start | (see CSV) | (see CSV) | (see CSV) | (see CSV) |
| development | hard | cold_start | (see CSV) | (see CSV) | (see CSV) | (see CSV) |

(Exact figures for every difficulty/method/split/source_type combination are in the CSV; this
prose table exists only to surface the standout pattern.)

**Combined across both splits, both methods (336,000 waypoint solves):**

- Overall waypoint stagnation rate = **48.20%** of all solves (161,965 / 336,000); among solves
  that failed the standard tier, **99.02%** have `failure_reason="stagnation"` (160,139 / 161,730)
  — stagnation is essentially the only failure mode at the waypoint level too, matching the
  point-IK-level and the already-published frozen aggregate (93,765 stagnation vs. 1,952
  `max_iterations`, frozen; 88,219 vs. 1,083, development — `final_dls_summary.json::
  *.failures.failure_reason_counts`, combined across point-IK + trajectory + both methods in that
  published field).
- `cold_start` stagnates far more than `warm_start` (58.4% vs. 38.0% of all solves) — consistent
  with warm-start's better seed (previous waypoint's solution) reducing (not eliminating) descent
  failures.
- `core` trajectories stagnate less than `random_challenge` (45.4% vs. 51.9%) — challenge
  trajectories' bounded-Fourier joint curves appear to produce harder seeds/targets on average.
- `hard`/`medium` difficulty trials stagnate more than `easy` (49.3%/53.9% vs. 41.4%), as expected
  from the trial-difficulty construction, but the gap is smaller than the warm/cold gap — **initial
  seed strategy (warm vs. cold) matters at least as much as the trial's own difficulty label**.
- Joint-limit margin at the final (post-solve) state is **exactly zero** for a large share of
  waypoint solves — 41-74% depending on difficulty/method/split (see CSV
  `percentage_final_margin_zero` column) — this is examined further in §8.

## 6. Waypoint-0 analysis

Full table: `docs/srpdik/srpdik_waypoint0_analysis.csv` (12 rows: 2 splits × 3 difficulty classes
× 2 methods; warm/cold are identical at waypoint 0 by construction — both start from the trial's
`q_initial` — so the small differences between the warm/cold rows for the same
split/difficulty are read as index-order/tie-breaking noise, not a real warm-vs-cold effect at
waypoint 0 itself).

| split | difficulty | wp0 success_standard_rate | wp0 stagnation_rate | median wp0 iterations | median final σ_min | median final margin | % final margin = 0 |
|---|---|---:|---:|---:|---:|---:|---:|
| development | easy | 0.443 | 0.543 | 20.0 | 0.120 | 0.0 | 0.529 |
| development | medium | 0.329 | 0.671 | 28.5 | 0.135 | 0.0 | 0.743 |
| development | hard | 0.343 | 0.657 | 32.0 | 0.090 | 0.0 | 0.586 |
| validation | easy | 0.429 | 0.557 | 17.5 | 0.110 | 0.0 | 0.414 |
| validation | medium | 0.429 | 0.571 | 23.5 | 0.095 | 0.0 | 0.529 |
| validation | hard | 0.357 | 0.614 | 30.5 | 0.117 | 0.0 | 0.557 |

**Waypoint 0 is already a substantial failure point**: standard-tier success at waypoint 0 is
33-44%, *lower* than the full-trajectory warm-start standard success rate (56.6% dev / 69.1% val)
— i.e. waypoint 0 is not an easy warm-up step, it fails **more** often than the trajectory-wide
average, and `stagnation` accounts for 54-67% of waypoint-0 attempts. This matches
`docs/srpdik/DLS_TRAJECTORY_PLOT_DIAGNOSIS.md`'s independently-sampled 3-trial finding that
waypoint 0 failed with `stagnation` in **all three** hand-picked easy/medium/hard trials.

Correlation with what happens later in the trajectory (development split, both methods pooled):

- Mean `maximum_failure_streak` when waypoint 0 **succeeds**: ~7-83 waypoints (varies by
  difficulty/method); when waypoint 0 **fails**: ~145-352 waypoints — i.e. **trials whose
  waypoint 0 fails go on to have much longer failure streaks** later in the same trajectory.
- Mean `coverage_ratio` (tier 3) when waypoint 0 succeeds is close to 1.0 in most groups; when
  waypoint 0 fails it is markedly worse in several groups (e.g. development/easy/cold_start: 1.76
  vs. 6.30 — the coverage-ratio metric here is not bounded to [0,1] in the underlying `tier3`
  computation for failed-early trials, so this is reported as an association signal, not a
  calibrated ratio comparison; see `evaluation_v2/metrics.py::compute_tracking` for the exact
  definition, not re-derived in this phase).

This is an **association**, not a proven causal claim — no intervention/ablation was run this
phase (per the scope restriction).

**H1 vs. H2 (why waypoint 0 fails):**

- H1 — `q_initial` already sits at/near a joint limit before any DLS iteration runs.
- H2 — `q_initial` is a valid interior point, but the DLS iteration itself walks the joint state
  to a limit and stalls there.
- H3 — the available summaries cannot distinguish H1 from H2.

**Conclusion: `UNKNOWN_H1_VS_H2`.** The only per-waypoint margin/σ_min fields available in the
permitted summaries (`waypoint_results.csv::minimum_joint_limit_margin`, `sigma_min`) are
**post-solve** (final) values — there is no `initial_joint_limit_margin`/`initial_sigma_min`
column for trajectory waypoints in `evaluate_trajectory_trial`'s output (confirmed against the
CSV header; see `SRPDIK_SOURCE_MAP.md`'s row for `evaluation_v2/trajectory_eval.py`), and no
per-iteration trace exists anywhere in the current repo (`kinematics/dls_solver.py::
dls_single_update` does not persist per-iteration history unless `record_history=True`, which
was never invoked for these runs). This exactly matches the prior, independently-produced
`DLS_TRAJECTORY_PLOT_DIAGNOSIS.md`'s own "UNKNOWN: exact iteration-by-iteration cause of
stagnation at minimum_joint_limit_margin=0.0" conclusion — an unrelated read-only pass over the
same data reached the identical UNKNOWN, which cross-validates that this is a genuine data gap,
not an oversight of this pass.

**Exact future diagnostic requirement** (do not implement in this phase): re-run
`solve_dls_until_converged(..., record_history=True)` for a small, explicitly-chosen sample of
waypoint-0 trials (or `dls_single_update` with a temporary per-iteration logger), read-only,
single-trial-at-a-time, to record `sigma_min`/`joint_limit_margin`/`Δq` at iteration 0 (=
`q_initial`, distinguishing H1) versus at the iteration where stagnation is declared
(distinguishing H2). This requires no change to the locked solver's behavior, only an
opt-in history capture already supported by `record_history=False/True` in
`solve_dls_until_converged`'s signature.

**Why doesn't actual waypoint 0 match target waypoint 0? Is this a plot bug? Is it in scope for
the SR-PPO-DLS initializer?**

- Not a plot bug (root cause proven in `docs/srpdik/DLS_TRAJECTORY_PLOT_DIAGNOSIS.md` §1/§5):
  `actual_position` at waypoint 0 is the correctly-computed `FK(q_solution)` of wherever the DLS
  attempt actually stopped; when that attempt fails (`success_standard=False`,
  `failure_reason="stagnation"`), the solution is genuinely far from the target. This phase's own
  quantitative pass (33-44% waypoint-0 standard success, 54-67% stagnation) confirms the same
  conclusion at full-dataset scale, not just the prior diagnosis's 3 hand-picked trials.
  A secondary, purely cosmetic issue exists in `visualization/plot_target_actual_3d.py` (it draws
  one continuous line through all 400 waypoints with no visual break at failed solves), which can
  make a real failure streak look like corrupted data — but that is a plotting presentation issue,
  separate from, and not the cause of, the real solver failure.
- Squarely in scope for SR-PPO-DLS: the PDF's entire premise (§1, §6.1) is that SR-PPO-DLS
  proposes a bounded residual correction to `q_initial` before the **first** DLS call of a
  sequence — which for the trajectory application (Reference Requirements item 13, "waypoint-0
  secondary application") is exactly waypoint 0. This phase's finding that waypoint 0 already
  fails 56-67% of the time via stagnation, and that its outcome correlates with much longer
  downstream failure streaks, is direct evidence that a better `q_initial` at waypoint 0 is a
  high-value target for SR-PPO-DLS, not a peripheral one.

## 7. Stagnation analysis

Combined across development + validation, all difficulties, both methods (336,000 waypoint
solves plus 2,400 point-IK solves considered separately in §4):

- Total waypoint-level stagnation: 161,965 / 336,000 = **48.20%** of all waypoint solves.
- Among waypoint solves that fail the standard tier (161,730 of 336,000): **99.02%**
  (160,139) have `failure_reason="stagnation"`. A small share of `stagnation`-tagged solves
  (1,826 / 161,965 = 1.13%) are still `success_standard=True` post-hoc — because the *solver's*
  own internal convergence check uses the **strict** tolerance (1 mm / 1°, `cand_D_pure_dls`'s
  `convergence_position_m`/`convergence_orientation_deg`), while the post-hoc `standard` tier used
  for reporting is coarser (3 mm / 2°); a solve can stagnate just past the strict tolerance while
  still clearing the coarser standard tier.
- By difficulty (waypoint level): easy 41.4%, hard 49.3%, medium 53.9% — medium is *not*
  intermediate here; it is the worst of the three (development+validation pooled).
- By method: cold_start 58.4%, warm_start 38.0%.
- By trajectory source type: core 45.4%, random_challenge 51.9%.
- By waypoint position: stagnation rate at waypoint_id==0 is **60.2%**, versus **48.2%** at
  waypoint_id>0 — waypoint 0 stagnates *more* than the trajectory average, reinforcing §6.

**Binned associations** (quantile bin edges derived from the development pool only, never from
frozen data, per the governing prompt's binning policy):

- Final σ_min quartile bins (development pool edges: 0.00025, 0.0778, 0.142, 0.198, 0.271):
  stagnation rate is **61.8%** in the lowest σ_min quartile vs. 38.9%/44.6%/48.0% in the upper
  three — a real but not perfectly monotonic association between low final singular value and
  stagnation.
- Final joint-limit-margin bins (development pool quartile edges collapse to two effective bins,
  0/0/0/0.089/0.667, because ≥50% of the development pool's final margins are exactly 0):
  stagnation rate is **62.9%** when final margin ≤0.089 vs. **12.8%** when final margin >0.089 —
  the strongest single association found in this phase.
- Position-error quartile bins: stagnation rate rises sharply from ~5-7% in the two lowest
  quartiles to **98.7%/100%** in the top two — nearly tautological (a solve with large final
  position error is, almost by definition, one that did not converge), reported for completeness
  but not treated as an independent finding.
- Orientation-error quartile bins: same pattern (0%, 11.0%, 99.7%, 100%).

**Association, not causation**: no iteration-level trace or controlled intervention was run this
phase (`record_history` was never invoked; see §6). The margin/σ_min associations are consistent
with, but do not prove, a mechanism where the DLS iteration walks toward — and stalls at — a
joint-limit boundary or a locally singular configuration. Whether failure propagation *starts* at
waypoint 0 specifically, versus emerging mid-trajectory, is addressed by the waypoint-0-vs-rest
comparison above (60.2% vs. 48.2%): waypoint 0 is disproportionately, but not exclusively, where
stagnation begins.

## 8. Joint-limit and singularity findings

- `cand_D_pure_dls` has `joint_limit_avoidance=false`, `null_space_gain=0.0` — the null-space
  joint-centering secondary task is **off** by design (this is *the* candidate whose selection
  rationale, per `docs/CHATGPT_DLS_CURRENT_STATE_BRIEF.md` §10, was to isolate the pure-DLS term;
  it was selected over candidates with centering on). This is a plausible structural contributor
  to the high final-margin=0 rate: nothing in the locked solver actively pushes the joint state
  away from a limit once `clip_to_operational_limits` engages.
- `minimum_joint_limit_margin == 0` (exactly at a boundary, not merely small) occurs in 41-74% of
  waypoint solves depending on difficulty/method/split, and in up to 56% for at least one
  point-IK/trajectory group combination inspected. This is far too frequent to be an edge case —
  it is a first-order property of this candidate's behavior on hard initial states.
- Point-IK `near_joint_limit` group (by construction, initial/target pairs near a limit):
  development standard success 0.940 (188/200), median iterations 26.3 (vs. 1-2 for
  `near_target`/`medium_target`) — succeeds most of the time, but at a real iteration cost, and
  its failures are a roughly even split of `stagnation` and `max_iterations` (unlike
  `large_orientation_change`, which is 100% `stagnation`).
- Point-IK `near_singularity` group (σ_min ≤ 0.03 by construction): development standard success
  0.960 (192/200), median iterations 31.0, again a mix of `stagnation` (8) and `max_iterations`
  (8) failures. The adaptive-damping schedule (`kinematics/adaptive_damping.py`) is designed
  specifically to keep this group numerically safe (0 non-finite results anywhere in the frozen
  run), and it succeeds at that — the cost shows up as iteration count, not instability.
- **Initial** joint-limit margin and **initial** σ_min are not available for trajectory waypoints
  in the permitted summaries (§1); only the point-IK group's `initial_sigma_min` column exists.
  This is the same gap that drives the `UNKNOWN_H1_VS_H2` conclusion in §6.

## 9. Plot bug versus real DLS failure

See §6 for the full answer. Summary: the previously-diagnosed "actual curve looks chaotic" symptom
in `visualization/plot_target_actual_3d.py` is a **real, correctly-recorded DLS stagnation
failure**, not a data or plotting-logic bug, though the plot's lack of a visual break at failed
waypoints is a genuine (separate, cosmetic) presentation issue. This phase's full-dataset
aggregation confirms the prior 3-trial diagnosis was representative, not an unlucky sample.

## 10. Những điều đã biết (known findings)

1. Stagnation is the overwhelming dominant failure mode at every level examined — point-IK
   (100% of `large_orientation_change` failures; mixed with `max_iterations` in
   `near_joint_limit`/`near_singularity`), trajectory waypoints (99.02% of standard-tier
   failures), and the previously-published frozen aggregate (93,765 vs. 1,952 `max_iterations`).
   A deeper iteration budget alone does not fix this (`cand_D_pure_dls` already uses 300
   iterations; candidates B-E, also 300 iterations, did not outperform it per
   `docs/CHATGPT_DLS_CURRENT_STATE_BRIEF.md` §10).
2. `large_orientation_change` is the single hardest point-IK group (89.5% dev/val standard
   success, 100% of its failures are stagnation).
3. Cold-start trajectories stagnate far more than warm-start (58.4% vs. 38.0% of all waypoint
   solves, dev+val pooled) — strong dependence on seed quality, exactly the redundancy-resolution
   weakness the PDF's SR-PPO-DLS design targets.
4. Waypoint 0 is disproportionately failure-prone (33-44% standard success, 54-67% stagnation,
   worse than the trajectory-wide average) and its outcome correlates with much longer downstream
   failure streaks — direct quantitative support for SR-PPO-DLS's waypoint-0 initializer framing.
5. Final joint-limit margin is exactly zero in a large share of waypoint solves (41-74%
   depending on group) and is strongly associated with stagnation (62.9% vs. 12.8% stagnation
   rate across the two effective margin bins).
6. The waypoint-0 "actual far from target" symptom previously flagged as a possible plot bug is
   confirmed, at full-dataset scale, to be a real solver failure, not a data/plotting defect
   (though the plot's failed-waypoint visual distinction is a real, separate, minor issue).

## 11. Những điều UNKNOWN

1. **`UNKNOWN_H1_VS_H2`** (§6): whether waypoint-0 stagnation is driven by `q_initial` already
   being at/near a joint limit (H1) versus the DLS iteration itself walking to a limit and
   stalling (H2). Requires an iteration-level trace (`record_history=True`) or an initial-state
   margin/σ_min field not present in any permitted summary this phase.
2. Whether the σ_min/margin associations with stagnation (§7) are causal or merely correlated
   with "hard target" more generally (large position/orientation error also correlates with
   stagnation almost tautologically) — no controlled ablation was run.
3. Fine-grained trajectory shape family (line/circle/figure8/helix/free_form) and challenge
   family (e.g. `near_limit_region`, `near_singular_region`) breakdowns were **not** computed this
   phase — `trajectory_trial_summaries.csv`'s `trajectory_family` column only distinguishes
   `core` vs. `random_challenge` at this granularity; finer family names live in
   `combined_trajectory_manifest.csv`/per-trajectory source manifests, not opened this phase to
   keep scope to the named permitted summary sources. `docs/CHATGPT_DLS_CURRENT_STATE_BRIEF.md`
   §10 flags the same gap as unaggregated.
4. Frozen-split per-difficulty-group / per-family / per-trial breakdowns do not exist in this
   analysis at all (§1) — only the published aggregate. If a future phase needs them, it must
   either extend the public export or accept that Phase 1A's frozen-split rows stay
   aggregate-only permanently (the `frozen_test` split's raw files remain access-denied by
   `srpdik/data/split_guard.py` outside of a single official run).
5. Whether `joint_limit_avoidance=false`/`null_space_gain=0.0` (candidate D's defining
   characteristic) is a *causal* contributor to the high margin-zero rate, versus those
   parameters being incidental to a candidate that happened to also be the frozen selection — not
   tested (would require comparing against candidates A/B/C/E's own per-waypoint margin data,
   which exist in `mpdik_kassow_v2_eval_devval/development/cand_{A,B,C,E}_*` but were out of scope
   for this cand_D-focused pass).

## 12. Implications for SR-PPO-DLS

- The dominant, nearly-exclusive failure mode (`stagnation`) is exactly the failure mode SR-PPO-DLS
  is designed to address (H2 in the PDF's own hypothesis framing, Reference Requirements item 1)
  — a descent/basin failure, not a numerical-safety or budget failure. This supports the PDF's
  core premise directly.
- `large_orientation_change` (point-IK) and low-final-margin / low-final-σ_min waypoints
  (trajectory) are natural high-value curriculum targets — see the `stagnation_rescue`,
  `joint_limit_sensitive`, and `near_singularity`/`large_orientation` strata in
  `docs/srpdik/SRPDIK_TRAINING_STRATA_SPEC.md`.
- Waypoint 0's outsized failure rate and its correlation with long downstream failure streaks
  directly justifies the PDF's waypoint-0-only initializer scope (Reference Requirements item 13,
  `DECISIONS.md` #7: no PPO re-invocation mid-trajectory) — fixing the seed once, at waypoint 0,
  has leverage over the entire subsequent chain.
- The `near_target`/`medium_target` point-IK groups (100% success, 1-2 median iterations) are the
  clearest available `do_no_harm` training signal — SR-PPO-DLS must learn `a≈0` here, and this
  phase's data confirms these groups are large enough (200/1200 dev samples each) and clean enough
  (zero failures) to serve that purpose directly.
- The missing initial-state margin/σ_min fields (§1, §6, §11) are a concrete Phase 2 requirement:
  the independent SR-PPO-DLS training-stream generator (Reference Requirements item 11) must
  record these fields at generation time, since the existing dev/val/frozen evaluation summaries
  do not carry them for trajectory waypoints.

## 13. Traceability

| Claim | Source file | Key/column |
|---|---|---|
| Reconciled success rates (§3) | `KR810_Tier0_Tier4_Dataset_v2.0.0/final_dls_summary.json` | `{split}.point_ik.*`, `{split}.{warm_start,cold_start}.trial_macro_success_standard` |
| Point-IK per-group table (§4) | `docs/srpdik/srpdik_dls_failure_mode_table.csv` | `result_type=point_ik` rows |
| Trajectory per-group table (§5) | `docs/srpdik/srpdik_dls_failure_mode_table.csv` | `result_type=trajectory` rows |
| Waypoint-0 table (§6) | `docs/srpdik/srpdik_waypoint0_analysis.csv` | all rows |
| Stagnation aggregates (§7) | computed from `mpdik_kassow_v2_eval_devval/{development,validation}/cand_D_pure_dls/tier2_sequential_dls/waypoint_results.csv` | `failure_reason`, `sigma_min`, `minimum_joint_limit_margin`, `position_error_m`, `orientation_error_deg` |
| Candidate D locked parameters (§8) | `configs/srpdik/dls_locked.json` | `joint_limit_policy`, `resolved_parameters` |
| Plot-bug finding (§9) | `docs/srpdik/DLS_TRAJECTORY_PLOT_DIAGNOSIS.md` | §1, §5 |
| Machine-readable rollup | `docs/srpdik/srpdik_dls_baseline_summary.json` | whole file |

## Data/frozen access confirmation

`raw_frozen_accessed=false`, `frozen_public_summary_used=true`, `protected_data_accessed=false`,
`dataset_v1_modified=false`, `dataset_v2_modified=false`, `dls_source_modified=false`,
`evaluation_rerun=false`, `training_run=false`. See `docs/srpdik/srpdik_dls_baseline_summary.json`
for the machine-readable form of this same statement.
