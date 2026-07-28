# SR-PPO-DLS — Training-Data Strata Spec (Phase 1A)

Defines the training-data strata Phase 2's independent training-stream generator
(`srpdik/pipelines/build_sr_ppo_training_stream.py`, Reference Requirements item 11) should
sample from. Grounded in `docs/srpdik/SRPDIK_DLS_BASELINE_FAILURE_ANALYSIS.md`. No stratum here
is a Phase 2 implementation — this is a design lock for what Phase 2 must build toward.

## 1. Strata definitions

Ordered by assignment priority (highest first — see §2 for exclusivity policy). Each stratum's
"available source fields" cites what the *training-stream generator* will produce (mirroring
`dataset_v2/point_ik_generation.py`/trial-generation logic per Reference Requirements item 11),
not the dev/val/frozen splits themselves (which must never be used to design generators or tune
thresholds, per `CLAUDE.md`).

### 1. `joint_limit_sensitive`

- **Definition**: task whose initial or (paired pure-DLS baseline) final state sits at/near a
  joint limit.
- **Inclusion predicate**: `minimum_initial_limit_margin_normalized <= near_joint_limit.
  threshold_normalized` (0.024991237796029034, `configs/difficulty_thresholds.json`) **or**
  paired baseline `B`'s final `minimum_joint_limit_margin <= 0`.
- **Exclusion predicate**: none beyond the inclusion predicate (a task may also match a
  lower-priority stratum's predicate; priority resolves the conflict, see §2).
- **Priority**: 1 (highest).
- **Available source fields**: `minimum_initial_limit_margin_normalized` (generation-time
  covariate, point-IK-style pool), paired baseline `B.final_joint_limit_margin` (from
  `srpdik/sr_ppo_dls/baseline_cache.py`, Phase C).
- **Estimated available count**: point-IK `near_joint_limit` group is 1/6 of the pool by
  construction (200/1200 per split in the existing dev/val Point-IK pools — the training stream
  will use its own independent pool at whatever size Phase 2 sets, but the *proportion* is
  expected to be similar since it reuses the same generation logic). At the trajectory-waypoint
  level, this phase measured 41-74% of waypoint solves ending with final margin exactly 0
  (`docs/srpdik/srpdik_dls_failure_mode_table.csv`), so the *baseline-final-margin* half of this
  predicate is expected to match a large fraction of trajectory-shaped training tasks.
- **Recommended sampling share**: 15%.
- **Reward emphasis**: `c_m` (joint-limit-margin penalty term, §7 PDF) should be weighted highly
  for this stratum specifically — do-no-harm on margin is the safety-relevant property, not just
  success rate.
- **Safety concern**: highest of all strata — a residual that pushes `q_seed` further into a
  limit is exactly what the projection step (Reference Requirements item 5) and safety filter
  (item 6) exist to prevent. This stratum is the primary test of the safety filter's Layer 1 hard
  floor.
- **Smoke/pilot/full**: usable in all three (smoke should include at least a handful of these
  tasks specifically to exercise the safety filter early).
- **Status**: DATA-SUPPORTED (predicate + prevalence grounded in measured Phase 1A data);
  sampling share PROPOSED.

### 2. `near_singularity`

- **Definition**: task near a kinematic singularity (low minimum singular value).
- **Inclusion predicate**: `initial_sigma_min <= singularity_sigma_threshold` (0.03,
  shared config key, `configs/difficulty_thresholds.json`/`configs/dls_config.json`).
- **Exclusion predicate**: excludes tasks already claimed by `joint_limit_sensitive` (priority 1).
- **Priority**: 2.
- **Available source fields**: `initial_sigma_min` (point-IK pool covariate; for trajectory
  waypoints, only paired-baseline *final* `sigma_min` is available — see
  `SRPDIK_DLS_BASELINE_FAILURE_ANALYSIS.md` §1/§11 on the missing-initial-field gap).
- **Estimated available count**: point-IK `near_singularity` group = 1/6 of pool (200/1200 in
  the existing dev/val pools); this phase measured 96.0% dev / 97.5% val standard success for
  this group but with median 31/6.3 iterations respectively (successes cost iterations) and a
  mix of `stagnation`/`max_iterations` failures (8/8 of 200 in dev).
- **Recommended sampling share**: 10%.
- **Reward emphasis**: `c_σ` (near-singularity penalty on `q_seed`).
- **Safety concern**: moderate — the locked adaptive-damping schedule already keeps this group
  numerically safe (0 non-finite results anywhere in the frozen run); the risk here is SR-PPO-DLS
  proposing a seed that *creates* a singularity that wasn't there in `q_initial`.
- **Smoke/pilot/full**: all three.
- **Status**: DATA-SUPPORTED; sampling share PROPOSED.

### 3. `stagnation_rescue`

- **Definition**: pure-DLS baseline `B` fails specifically via `failure_reason="stagnation"` —
  the primary rescue target of the entire method (PDF hypothesis H2, Reference Requirements
  item 1).
- **Inclusion predicate**: paired baseline `B.failure_reason == "stagnation"` (checked after
  running the paired pure-DLS baseline, Reference Requirements item 8 — this stratum is defined
  on the *outcome* of the locked solver, not on an input covariate alone).
- **Exclusion predicate**: excludes tasks already claimed by strata 1-2 (a stagnating task that is
  also near a joint limit or singularity is counted there first, since those failure mechanisms
  are more specifically actionable by the safety filter/projection).
- **Priority**: 3.
- **Available source fields**: `B.failure_reason`, `B.iterations`, `B.position_error_m`,
  `B.orientation_error_deg` (all produced by the paired baseline cache).
- **Estimated available count**: this is the **largest identified failure pool** in this phase's
  data — point-IK `large_orientation_change` group (21/200 dev, 27/200 val stagnation failures,
  100% of that group's failures); trajectory waypoints show 48.2% overall stagnation rate
  (161,965/336,000 dev+val combined) after excluding the higher-priority margin/singularity
  overlap. Even a conservative independent-stream estimate puts this stratum at tens of thousands
  of candidate tasks at full scale.
- **Recommended sampling share**: 30% (largest single share — this is the PDF's stated primary
  objective).
- **Reward emphasis**: rescue bonus `c_R(1-S_B)S_H` should dominate for this stratum specifically.
- **Safety concern**: moderate — the main risk is degradation (`c_D` term) on the subset of this
  stratum's tasks that a poorly-tuned residual pushes further from convergence rather than closer.
- **Smoke/pilot/full**: pilot and full only — a smoke test does not need the full rescue signal,
  just enough to confirm the pipeline runs without crashing (a handful suffice).
- **Status**: DATA-SUPPORTED; sampling share PROPOSED.

### 4. `large_orientation`

- **Definition**: task with large orientation displacement between `q_initial`'s pose and the
  target.
- **Inclusion predicate**: same generation-time predicate as the `large_orientation_change`
  Point-IK group (`position_orientation_thresholds`, `dataset_v2/point_ik_generation.py`), i.e.
  orientation distance above the pool's high quantile.
- **Exclusion predicate**: excludes tasks already claimed by strata 1-3.
- **Priority**: 4.
- **Available source fields**: `orientation_distance_rad` (generation-time covariate).
- **Estimated available count**: 1/6 of the point-IK pool by construction (200/1200 dev/val);
  this phase found it is simultaneously the **worst-performing** point-IK group (89.5% standard
  success both splits) and **100%-stagnation** in its failures — it substantially overlaps with
  `stagnation_rescue` (priority 3 claims the intersection; this stratum is left with the
  orientation-large-but-not-yet-failing subset for curriculum diversity).
- **Recommended sampling share**: 10%.
- **Reward emphasis**: `c_E` error-improvement term, orientation component weighted.
- **Safety concern**: low-moderate.
- **Smoke/pilot/full**: pilot and full.
- **Status**: DATA-SUPPORTED; sampling share PROPOSED.

### 5. `far_target`

- **Definition**: task with large position displacement between `q_initial`'s pose and the
  target.
- **Inclusion predicate**: same generation-time predicate as the `far_target` Point-IK group
  (position distance in the pool's mid-high quantile band, between `medium_target` and
  `large_orientation_change`/`near_joint_limit`/`near_singularity` in priority).
- **Exclusion predicate**: excludes tasks already claimed by strata 1-4.
- **Priority**: 5.
- **Available source fields**: `position_distance_m` (generation-time covariate).
- **Estimated available count**: 1/6 of the point-IK pool (200/1200 dev/val); this phase measured
  98.5% dev / 97.5% val standard success — the **best-performing** of the four "hard" groups, with
  only 3/200 (dev) and 5/200 (val) failures, all `stagnation` or 1 `max_iterations`.
- **Recommended sampling share**: 5% (smallest of the failure-adjacent strata — this group is
  already handled well by pure DLS, per the data).
- **Reward emphasis**: `c_E` position component.
- **Safety concern**: low.
- **Smoke/pilot/full**: pilot and full.
- **Status**: DATA-SUPPORTED; sampling share PROPOSED.

### 6. `high_iteration_success`

- **Definition**: pure-DLS baseline `B` succeeds, but at a high iteration cost — SR-PPO-DLS
  should reduce iterations without reducing success.
- **Inclusion predicate**: `B.success_standard == True` and `B.iterations >= p75(iterations |
  success)` (75th percentile of iterations-to-success, computed on the training stream's own
  pool at generation time, never on frozen data).
- **Exclusion predicate**: excludes tasks already claimed by strata 1-5 (a successful-but-slow
  task that is also near a limit/singularity is counted there first).
- **Priority**: 6.
- **Available source fields**: `B.success_standard`, `B.iterations`.
- **Estimated available count**: point-IK `near_joint_limit` (188/200 dev successes, median 26.3
  iterations) and `near_singularity` (192/200 dev successes, median 31.0 iterations) groups are
  the clearest examples — both far above the `near_target`/`medium_target` median of 1-2
  iterations. Combined, a substantial fraction of the two "near-*" groups' successes qualify.
- **Recommended sampling share**: 10%.
- **Reward emphasis**: `c_I` iteration-improvement term (only active when both `B` and `H`
  succeed, per the PDF's reward formula).
- **Safety concern**: low — the base task already succeeds; the risk is purely a degradation into
  failure, covered by `c_D`.
- **Smoke/pilot/full**: full only (not needed for smoke/pilot correctness checks).
- **Status**: DATA-SUPPORTED; sampling share PROPOSED.

### 7. `do_no_harm`

- **Definition**: pure-DLS baseline `B` already succeeds with very few iterations — SR-PPO-DLS
  must learn `a ≈ 0` (the hard do-no-harm invariant, Reference Requirements item 4).
- **Inclusion predicate**: `B.success_standard == True` and `B.iterations <= p25(iterations |
  success)` on the training stream's own pool.
- **Exclusion predicate**: excludes tasks already claimed by strata 1-6.
- **Priority**: 7.
- **Available source fields**: `B.success_standard`, `B.iterations`.
- **Estimated available count**: point-IK `near_target` (200/200 dev, median 1 iteration) and
  `medium_target` (200/200 dev, median 2 iterations) groups are the direct evidence — 1/3 of the
  point-IK pool by construction, 100% success, near-minimal iteration counts, in both dev and
  validation.
- **Recommended sampling share**: 10%.
- **Reward emphasis**: action-norm penalty `c_a‖a‖²` should be the dominant term for this
  stratum; near-zero degradation is expected almost by definition.
- **Safety concern**: low, but this is the stratum that most directly tests whether the
  do-no-harm invariant actually holds in practice (not just architecturally, via `a=0 ⇒
  q_cand=q_initial`).
- **Smoke/pilot/full**: all three — this is the minimum viable stratum for a smoke test (cheapest
  to simulate, fastest to detect a broken pipeline).
- **Status**: DATA-SUPPORTED; sampling share PROPOSED.

### 8. `balanced_regular`

- **Definition**: residual/complement coverage sampled independent of the outcome-based priority
  above, to prevent the policy from only ever seeing failure-adjacent or trivial-success cases
  and losing generalization over the full Point-IK/trajectory distribution (PDF §8.2 curriculum
  stage 3, "balanced across 6 difficulty groups").
- **Inclusion predicate**: uniform draw across all 6 point-IK difficulty groups (and, for
  trajectory, all difficulty/method/source-type combinations) regardless of which stratum 1-7 a
  given draw would otherwise match — this stratum is sampled from the **full population**, not
  from a residual after strata 1-7 are removed.
- **Exclusion predicate**: none — by definition this stratum overlaps strata 1-7 (see §2's
  multi-label note).
- **Priority**: 8 (lowest priority for *label assignment* in a strict-partition reading, but
  sampled independently — see §2).
- **Available source fields**: same generation-time covariates as strata 1-5, drawn uniformly.
- **Estimated available count**: unbounded — this is a resampling policy over the full pool, not
  a filtered subset.
- **Recommended sampling share**: 10%.
- **Reward emphasis**: none specific — this stratum exists for coverage, not a targeted reward
  shape.
- **Safety concern**: low.
- **Smoke/pilot/full**: pilot and full (a smoke test can skip this in favor of `do_no_harm` +
  a minimal `stagnation_rescue` sample).
- **Status**: PROPOSED (this stratum's role is a design choice, not directly measured).

## 2. Priority / exclusivity

Strata 1-7 are assigned by **strict priority order** (1 highest): a task is labeled with the
*first* stratum (in priority order) whose inclusion predicate it matches, even if it would also
match a lower-priority stratum's predicate. This mirrors the existing dataset v2 point-IK
classification pattern (`CLASSIFICATION_PRIORITY_HIGHEST_FIRST` in
`dataset_v2/config_templates.py`), reused deliberately for consistency.

`balanced_regular` (stratum 8) is the one **explicit multi-label exception**: it is sampled
independently, from the full population, without checking whether a drawn task already carries a
priority 1-7 label. A single task may therefore appear in the training stream tagged both as (say)
`stagnation_rescue` *and*, on a separate draw, as `balanced_regular` — this is intentional (the
point of `balanced_regular` is unfiltered coverage) and must be logged as a dual/overlapping
sampling event, not silently deduplicated, so Phase 2's acceptance gates can distinguish "coverage
sampling" from "targeted rescue sampling" in the training-stream manifest.

## 3. Sampling recommendation

| stratum | share | status |
|---|---:|---|
| `stagnation_rescue` | 30% | PROPOSED |
| `joint_limit_sensitive` | 15% | PROPOSED |
| `near_singularity` | 10% | PROPOSED |
| `large_orientation` | 10% | PROPOSED |
| `high_iteration_success` | 10% | PROPOSED |
| `do_no_harm` | 10% | PROPOSED |
| `balanced_regular` | 10% | PROPOSED |
| `far_target` | 5% | PROPOSED |
| **total** | **100%** | |

These shares are **not locked**. Per the governing prompt's instruction, no final ratio is locked
until Phase 2's training-stream generator exists and can report actual per-stratum population
sizes at the independent-stream's chosen scale; TPE hyperparameter search (Reference Requirements
item 9/PDF §8.5) may retune the curriculum-stage sampling weights derived from this table.

## 4. Smoke/pilot/full use

| stratum | smoke | pilot | full |
|---|---|---|---|
| `do_no_harm` | yes | yes | yes |
| `joint_limit_sensitive` | yes (minimal) | yes | yes |
| `near_singularity` | no | yes | yes |
| `stagnation_rescue` | no | yes | yes |
| `large_orientation` | no | yes | yes |
| `far_target` | no | yes | yes |
| `high_iteration_success` | no | no | yes |
| `balanced_regular` | no | yes | yes |

Smoke tests should stay minimal (cheapest do-no-harm + a handful of joint-limit-sensitive tasks to
exercise the safety filter) — full statistical coverage is a pilot/full concern.

## 5. Leakage restrictions

- Every stratum's inclusion predicate must be evaluable from the **independent training-stream
  pool** (Reference Requirements item 11), generated with its own `derive_seed`/`rng_from` tag
  namespace (`dataset_v2/seeds.py`, called with a new tag, never modified) — never from
  development/validation/frozen_test directly as the *only* source, per `CLAUDE.md`'s
  `frozen_test` rule and the PDF's §9.1/§9.3 anti-leakage requirement.
- None of the 8 strata's predicates reference a protected field
  (`evaluation_v2/protected_guard.py::PROTECTED_FIELD_NAMES` — `q_reference`,
  `q_target_reference`, `q_reference_start`, `q_source_reference`,
  `position_reconstruction_error_m`, `orientation_reconstruction_error_rad`,
  `waypoint_reachable`). All predicates use `q_initial`-derived covariates (margin, σ_min,
  position/orientation distance) or paired-baseline `B` outcomes (`failure_reason`, `iterations`,
  `success_standard`) — never a target-solution joint state.
- `frozen_test` must never be used to derive any stratum's threshold or population estimate — the
  quantile-derived thresholds this document cites (`p75`/`p25` for iteration-based strata) are
  computed **on the training stream's own pool**, mirroring the same policy already used for
  Point-IK generation (`_derive_position_orientation_thresholds`, computed per-pool, never on
  frozen data).
- Content-hash disjointness between the training stream and dev/val/frozen must be verified
  (Reference Requirements item 11) before any stratum is populated for training — this is a Phase
  2 gate, not evaluated in this phase.

## 6. Fields required in Phase 2

For every training-stream task, at minimum: `sample_id`/`task_id` (join key), `q_initial`,
`target_position`, `target_quaternion_wxyz`, `difficulty_id`/`name` (report/ablation only, never
policy input, per Reference Requirements item 12), `minimum_initial_limit_margin_normalized`,
`initial_sigma_min`, `position_distance_m`, `orientation_distance_rad`, paired baseline `B`'s
`success_{coarse,standard,strict}`, `failure_reason`, `iterations`, `position_error_m`,
`orientation_error_deg`, `final_joint_limit_margin`, `final_sigma_min`. This list directly closes
the initial-margin/σ_min gap identified in
`SRPDIK_DLS_BASELINE_FAILURE_ANALYSIS.md` §1/§6/§11 — Phase 2's generator must record these at
generation time since the existing dev/val/frozen evaluation summaries do not carry them for
trajectory-shaped tasks.

## 7. Acceptance gates for the generated training stream

Before any stratum is used for training (Phase 2 gate, not evaluated here):

1. Every stratum's inclusion/exclusion predicate is implemented and unit-tested against a small
   synthetic fixture (not against real dev/val/frozen data, to avoid design-on-frozen leakage).
2. Content-hash disjointness confirmed between the training stream and all three fixed splits.
3. No protected field appears in any stratum's task record (`assert_no_protected_fields`-style
   guard, reused or mirrored per Reference Requirements item 12).
4. Measured per-stratum population sizes at the chosen training-stream scale are reported and
   compared against this document's `estimated available count` qualitative claims — if a
   stratum turns out near-empty (e.g., if the independent stream's `stagnation_rescue` rate is
   much lower than the 48% measured here on dev/val), the sampling shares in §3 must be revisited
   before locking a curriculum.
5. Sampling shares sum to exactly 100% (or 1.0) in the generated manifest, with `balanced_regular`
   explicitly logged as an overlapping (non-exclusive) draw per §2.
6. `do_no_harm` and `joint_limit_sensitive` are present even in the smoke-scale stream (per §4).
