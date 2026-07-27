# Current DLS Problem and Dataset Audit — Kassow KR810

> Read-only audit of `D:\data\hoang_anh`. Every claim below is traceable to code, config,
> manifest, generated data, or a test in that tree. No file other than this one was created or
> modified; no generation, evaluation, or training was run.

## 1. Snapshot của source hiện tại

| Trường | Giá trị |
|---|---|
| Working directory | `D:\data\hoang_anh` (audit scope); implementation CWD `D:\data\hoang_anh\mpdik_kassow` |
| Repository root | `D:\data\hoang_anh\mpdik_kassow` — the **only** git repository. Siblings (`mpdik_kassow_v2_work`, `mpdik_kassow_v2_eval_*`, `mpdik_kassow_v2_protected_validation`, `KR810_Tier0_Tier4_Dataset_v2.0.0`, `release`) are external data roots, not repos |
| Branch | `feature/dataset-v2` |
| Commit | `151ffd76729aaa3d6f258a49e9cdfa8df768fb59` (2026-07-25) — "feat: complete frozen DLS evaluation and dataset v2 release" |
| VERSION | Repo/Dataset v1: `1.0.0` (`VERSION`). Dataset v2 work root: `2.0.0-dev`. Dataset v2 public release: `2.0.0` |
| Git status | Clean (0 porcelain lines) |
| Dataset đang được xem là hiện hành | **Dataset v2** (external roots + `KR810_Tier0_Tier4_Dataset_v2.0.0`) |
| Dataset v1 status | Generated + validated + checksummed, **immutable regression baseline**. Tier 0–4 *evaluation* on v1 was **never run** (`DATASET_MANIFEST.json::notes[2]`; no `results/` in repo; `temporary_results/` empty) |
| Dataset v2 status | Fully **generated, validated, frozen, evaluated (dev + validation + frozen_test), and released** as v2.0.0 (`docs/V2_IMPLEMENTATION_LOG.md` Phase 8B; `KR810_Tier0_Tier4_Dataset_v2.0.0/final_dls_summary.json`) |

**Conflicts found (documented, code/data taken as truth):**

1. `mpdik_kassow_v2_work/DATASET_MANIFEST.json::status = "scaffold"`, `generated: false`,
   `frozen: false`, and `notes[0] = "Phase 1 scaffold only: no Tier 0-4 data has been generated"`
   — **stale**. The same file's `counts.*.generated = true` and 494 generated files under the
   root contradict it. Same staleness in `configs/dataset_config.json::status`,
   `configs/seed_policy.json::status = "policy_defined_not_yet_used_for_generation"`,
   `configs/split_policy.json::status = "policy_defined_not_yet_enforced_by_generation"`.
   **Truth = the generated data + Phase 5–8 log.**
2. `README.md` lines 64–68 ("assets have **not** been integrated… they do not exist yet") vs
   `DATASET_MANIFEST.json::assets.status = "integrated"` and the actual populated
   `assets/kr810.xml` / `assets/kr810.urdf` / `assets/meshes/a810/*.stl`.
   **Truth = assets are integrated** (`tests/test_asset_loading.py` loads the MJCF in MuJoCo).
3. `specs/DLS_DATASET_V2_SPEC.md` line 3 says "Phase 0 (planning/spec only). Nothing … has been
   implemented" — superseded by the per-section `[LOCKED by Phase 5.x/6/7]` amendments in the
   same file and by the implementation log.
4. `mpdik_kassow_v2_eval_frozen/frozen_test/cand_D_pure_dls/run_manifest.json::frozen_test_accessed
   = false` is a **known stale hardcoded field** (self-declared in
   `frozen_access_report.json::known_defect`); authoritative record is
   `frozen_access_ledger.json` (`access_count = 1`) and `resolved_config.json::splits`.

## 2. Vấn đề nghiên cứu hiện tại

**Robot.** Kassow KR810, 7 revolute joints (`configs/robot_config.json::n_joints = 7`,
`nq = nv = 7`), simulated in MuJoCo from `assets/kr810.xml`, converted from
`assets/kr810.urdf` (`assets/ASSET_CONVERSION_REPORT.md`). Pose is measured at the MuJoCo site
`ee_site`, defined as the *link reference frame at the `end_effector` body origin* and explicitly
**not a calibrated TCP** (`assets/model_metadata.json::end_effector_definition`:
"This is NOT an officially calibrated TCP, tool tip, or flange calibration frame").

**Bài toán.** Numerical inverse kinematics: given a target 6-DoF pose
`(target_position, target_quaternion_wxyz)` and an initial joint state `q_initial`, find `q` such
that `FK(q)` matches the target within tolerance, using an iterative **Damped Least Squares**
solver (`kinematics/dls_solver.py::solve_dls_until_converged`).

**Redundancy.** The task is 6-D (3 position + 3 orientation); the arm has 7 joints, so
`J(q) ∈ ℝ^{6×7}` has a ≥1-dimensional null space (`kinematics/jacobian.py` — shape `(6, 7)`), and
IK has a continuum of solutions. The repo exploits this explicitly: the optional null-space
joint-centering term uses the projector `(I − J⁺J)`
(`kinematics/dls_solver.py::dls_single_update`, lines 182–188). Redundancy is also the stated
reason the v2 trial difficulty metric is a *pose* error, never a joint distance
(`configs/trial_config.json::difficulty.primary_metric`; spec section J.1: "never normalized joint
distance alone (the KR810 is redundant)").

**Những gì đang được đo (mỗi mục có nơi cài đặt):**

| Vấn đề | Đo ở đâu |
|---|---|
| Pose accuracy | `position_error_m`, `orientation_error_deg` per solve (`kinematics/dls_solver.py::DLSResult`) |
| Phụ thuộc initial configuration | warm_start vs cold_start (`algorithms/warm_start_dls.py`, `algorithms/cold_start_dls.py`); trial `easy/medium/hard` init classes (`configs/trial_config.json`) |
| Singularity | `sigma_min`, `condition_number`, `manipulability` (`kinematics/singularity_metrics.py`, `kinematics/manipulability.py`); difficulty group `near_singularity`; challenge family `near_singular_region` |
| Joint limit | `minimum_joint_limit_margin`, violation mask, clip (`kinematics/joint_limit_utils.py`); group `near_joint_limit`; family `near_limit_region` |
| Hội tụ | `success`, `iterations`, `failure_reason ∈ {max_iterations, stagnation, joint_limit_failure, non_finite_*, linear_solve_failure, invalid_target}` |
| Continuity | `recovered_after_previous_failure`, `recovery_rate`, `maximum_failure_streak` (`evaluation_v2/metrics.py::compute_trial_summaries`) |
| Trajectory tracking | Tier 3 (`evaluation/trajectory_metrics.py`, `evaluation/cross_track_metrics.py`) |
| Repeatability / robustness | **v1 only**: `trial_category ∈ {repeatability, robustness}`, 240/120 rows (`trajectories/trajectory_trials.csv`); v1's `evaluation/iso9283_metrics.py`. **v2 replaced this** with `easy/medium/hard` init classes — repeatability/robustness categories do **not** exist in Dataset v2 |
| Joint feasibility / smoothness | Tier 4 (`evaluation/smoothness_metrics.py`, `evaluation_v2/metrics.py::compute_tier4`) |

**Vì sao DLS baseline phải có trước MPDIK.** Stated directly in
`docs/DLS_FULL_EVALUATION_SPEC.md` section A: without a *full* (not smoke) DLS evaluation there is
no quantitative basis to claim MPDIK/PPO is better or worse. Dataset v2 executed exactly that:
one pre-registered candidate set → development selection → locked config → single frozen-test run
(`docs/V2_IMPLEMENTATION_LOG.md` Phase 8A/8B).

**Phạm vi.** Kinematics only. No dynamics, torque, actuator, controller, or collision anywhere in
`kinematics/`, `algorithms/`, `evaluation/`, `evaluation_v2/`, `pipelines/`
(`assets/model_metadata.json::known_limitations`: "No MuJoCo actuators are defined (nu=0)";
both dataset manifests set `includes_dynamic_control/ppo/mpdik/mappo: false`). No RL code exists
in the repo.

## 3. Dataset hiện có gồm những gì?

### 3.1 Dataset v1 (in-repo, immutable)

| Tier/dataset | Mục đích | Dữ liệu chính | Số lượng | Generator | Config | Validator/evaluator | Trạng thái |
|---|---|---|---:|---|---|---|---|
| Tier 0 FK states | FK sanity states | `benchmarks/validation/fk_test_states.npz` (`q_samples (1000,7)`, `group_id`, `source_seed`) | 1000 | `generators/generate_fk_validation_states.py` | `configs/benchmark_config.json` | `evaluation/kinematics_validation.py::validate_fk_states` | generated + checksummed |
| Tier 0 Jacobian states | analytic vs FD Jacobian | `benchmarks/validation/jacobian_test_states.npz` (+`finite_difference_epsilon`) | 200 | same | same | `::validate_jacobian_states` | generated |
| Tier 0 singularity states | σ_min / κ distribution | `benchmarks/validation/singularity_test_states.npz` (+`sigma_min`,`condition_number`) | 300 | same | same | `::validate_singularity_states` | generated |
| Tier 1 Point-IK | point IK benchmark | `benchmarks/point_ik/point_ik_v1.npz` — 16 arrays incl. `q_initial (1200,7)`, `q_target (1200,7)`, `target_position`, `target_quaternion`, covariates, `difficulty_id` | 1200 (6 groups × 200) | `generators/generate_point_ik_dataset.py` | `configs/benchmark_config.json` | `tests/test_point_dataset.py`, `benchmarks/point_ik/point_ik_checksum.json` | generated + validated |
| Tier 2–4 trajectories | waypoint chains | 8 × `trajectories/<type>/<id>.npz`, each `400` waypoints (`waypoint_id`, `time_s`, `path_parameter_s`, `target_position (400,3)`, `target_quaternion (400,4)`, `target_linear_velocity`, `target_linear_acceleration`) | 8 traj × 400 wp = 3200 poses | `generators/generate_{line,circle,figure8,helix}_trajectory.py`, `_trajectory_common.py` | `configs/trajectory_config.json` | `generators/validate_generated_targets.py`, `tests/test_trajectory_files.py` | generated + validated |
| Tier 2–4 trials | init states / speeds | `trajectories/trajectory_trials.csv` | 360 (= 8 × 3 speeds × (10 repeatability + 5 robustness)) | `_trajectory_common.py::build_trials` (`REPEATABILITY_REPEATS=10`, `ROBUSTNESS_INITIAL_CONFIGS=5`) | `configs/trajectory_config.json::speed_scales` | `tests/test_trajectory_files.py::test_trial_categories_and_counts` | generated |
| Tier 0–4 **evaluation** | — | — | 0 | — | `configs/experiment_presets.json` | `pipelines/run_tier0_to_tier4.py` | **implemented but never run** (`DATASET_MANIFEST.json::notes[2]`) |

v1 difficulty thresholds are quantile-derived from a 30,000-pair generic pool and stored in
`benchmarks/point_ik/difficulty_definition.json::quantile_thresholds`.

### 3.2 Dataset v2 (external dataset root — **not** in the repo)

Root: `D:\data\hoang_anh\mpdik_kassow_v2_work` (494 files). Public release copy:
`D:\data\hoang_anh\KR810_Tier0_Tier4_Dataset_v2.0.0` (v2.0.0). Locked counts in
`specs/DLS_DATASET_V2_SPEC.md` section B; realized counts confirmed on disk.

| Tier/dataset | Mục đích | Dữ liệu chính | Locked / Generated | Generator | Config | Validator | Trạng thái |
|---|---|---|---:|---|---|---|---|
| Tier 0 FK | FK states | `tier0_validation/fk_test_states_v2.npz` (`q_samples (1000,7)`, `ee_position`, `ee_quaternion_wxyz`, `minimum_joint_limit_margin`) | 1000 / 1000 (5 groups × 200) | `dataset_v2/tier0_generation.py::generate_fk_states` | `configs/tier0_config.json` | `dataset_v2/tier0_validation.py` | generated + validated |
| Tier 0 Jacobian | FD-check states | `jacobian_test_states_v2.npz` (+`sigma_min/max`,`condition_number`,`numerical_rank`) | 1000 / 1000 (5 groups × 200) | `::generate_jacobian_states` | same | same | generated + validated |
| Tier 0 singularity | σ_min classes | `singularity_test_states_v2.npz` (+`manipulability`) | 600 / 600 (regular/moderate/near_singular × 200) | `::generate_singularity_states` | same | same | generated + validated |
| Tier 1 Point-IK | point IK benchmark | `tier1_point_ik/{development,validation,frozen_test}.npz` — 24 arrays, incl. `sample_id (<U46)`, `q_initial`, `q_target_reference`, target pose, 12 covariates, `content_hash` | 6000 / 6000 (6 groups × 1000; split **1200 / 1200 / 3600**) | `dataset_v2/point_ik_generation.py::run_point_ik_generation` | `configs/point_ik_config.json`, `configs/difficulty_thresholds.json` | `dataset_v2/point_ik_validation.py` | generated + validated |
| Anchors | trajectory seed configurations | `anchors/anchors.npz` (25 arrays), `anchor_manifest.csv` | 12 / 12 = 6 `regular` + 3 `near_limit` + 3 `near_singular`; split 4/4/4 | `dataset_v2/anchor_generation.py::run_anchor_generation` | `configs/anchor_config.json` | `dataset_v2/anchor_validation.py`, `anchor_feasibility.py` | generated + validated + feasibility-checked |
| Core trajectories | deterministic shapes | `trajectories/<split>/core_*.npz` + `_source.npz`; canonical arrays incl. `target_position (400,3)`, `target_quaternion (400,4)`, `cumulative_arc_length_m`, `cumulative_angular_displacement_rad`, `q_reference (400,7)` (protected), `waypoint_reachable` | 120 / 120 (5 shapes × 2 orientation modes × 12 anchors); split **40/40/40** | `dataset_v2/core_trajectory_generation.py` | `configs/trajectory_config.json` | `core_trajectory_validation.py`, `generation_reachability.py` | generated + strict-reachability validated |
| Random challenge | randomized coverage | `trajectories/<split>/challenge_<split>_NNN.npz` + `_source.npz` | 90 / 90; split **30/30/30**; 6 families × 15 | `dataset_v2/challenge_trajectory_generation.py` | `configs/random_challenge_config.json` | `challenge_trajectory_validation.py` | generated + validated |
| Combined catalog | 210-row union | `trajectories/combined_trajectory_manifest.csv` | 210 / 210 (70 per split) | `pipelines/run_dataset_v2_combined_catalog.py` | — | `dataset_v2/trajectory_catalog.py` | validated |
| Trials | initial states | `trials/{split}.npz` (21 arrays incl. `q_initial (210,7)`, `primary_difficulty_metric`), `trials/protected/{split}_evidence.npz` | 630 / 630 (3 per trajectory: easy/medium/hard; 210 per split) | `dataset_v2/trial_generation.py::run_trial_generation` | `configs/trial_config.json` | `dataset_v2/trial_validation.py` | generated + validated |
| Checksums | integrity | `checksums/CHECKSUM_MANIFEST.json` | every generated file | `dataset_v2/checksums.py` | — | `tests/test_dataset_v2_release.py` | frozen |

Canonical waypoints: **400 per trajectory**, 210 × 400 = **84,000** canonical target poses
(`DATASET_MANIFEST.json::counts.canonical_poses_total`, matched on disk).

**Public vs protected.** The evaluation-facing export
(`mpdik_kassow_v2_eval_public`, `..._public_frozen`) strips 12 protected keys — including
`q_reference`, `q_target_reference`, `waypoint_reachable`, all `target_*` conditioning fields —
listed in `PUBLIC_EXPORT_MANIFEST.json::protected_keys_excluded`. `q_target_reference` is
**provenance only**: it is the joint state whose FK produced the target, never a solver output and
never an initial guess (`configs/point_ik_config.json::q_target_usage_policy`;
`tests/test_point_dls_algorithm.py::test_q_target_is_not_used_as_initial_guess`).

### 3.3 Luồng sinh dữ liệu (theo source thực tế)

```
master_seed=42  (configs/seed_policy.json)
  └─ dataset_v2/seeds.py::derive_seed(base, *tags)   [SHA-256 over canonical bytes, pure-int]
       ├─ component tag (tier0=10, point_ik=20, anchors=30, core=40, challenge=50, trials=60)
       └─ split tag (development=1, validation=2, frozen_test=3) [+ frozen_*_seed_revision]

Point-IK (dataset_v2/point_ik_generation.py::run_point_ik_generation):
  sample q_initial in operational interior (margin = 1% of each joint's half-range)
  → q_target_reference = clip(q_initial + logU(10^-2 .. 10^0.5) · unit_dir, lower, upper)
  → FK(q_target_reference) ⇒ reachable Cartesian target (never a freely chosen point)
  → _compute_pair_metrics: position/orientation/joint distance, σ_min & limit-margin at both ends
  → _derive_position_orientation_thresholds (33/66/85 percentiles of THIS pool)
  → _classify_pool with priority near_singularity > near_joint_limit > large_orientation_change
                                > far_target > medium_target > near_target
  → stratified_diversity_select (6 covariates × 4 quantile bins, round-robin to exactly 1000/group)
  → _split_group_selection ⇒ 200/200/600 per group
  → content_hash per sample + cross-split disjointness check ⇒ NPZ + manifest + report

Core trajectories (dataset_v2/core_trajectory_generation.py):
  anchor q (12) → closed-form shape geometry alternatives × scale bands
  → high-resolution source (source_waypoint_count_nominal) via quintic time scaling
  → arc-length-uniform resample to exactly 400 canonical waypoints (SLERP orientation)
  → STRICT reachability: per waypoint solve q_reference, then INDEPENDENT FK check
     (1e-4 m / 0.01 deg, generation_reachability_config.json) — solver success flag never sufficient
  → accept/reject whole (alternative, scale) candidate; never skip a waypoint
  → manifest + content hash + anti-leakage report

Random challenge (dataset_v2/challenge_trajectory_generation.py):
  independent reachable q_start (never an anchor)
  → bounded-Fourier joint curve q(s) = q_start + offset(s), amplitude capped by each joint's margin
  → FK(q(s)) ⇒ source poses (reachable by construction) → same 400-waypoint canonical resample
  → family coverage floors + strict FK reachability → diversity selection → full re-validation

Trials (dataset_v2/trial_generation.py):
  per trajectory: 1400-candidate q_initial pool from operational limits ONLY
     (500 interior + 300 limit-aware + 300 singularity-aware + 300 stratified)
  → primary metric = 0.5·(pos_err/0.9357 m) + 0.5·(SO(3) geodesic err/2.3014 rad) vs first target
  → non-overlapping easy/medium/hard bands with guard gaps; per band pick the median-closest
  → q_reference_start used ONLY as protected evidence, never as/into q_initial

Freeze: CHECKSUM_MANIFEST.json + per-tier reports + DATASET_MANIFEST/VERSION
```

## 4. DLS giải quyết bài toán như thế nào?

Central table. All steps are inside one `solve_dls_until_converged` call unless noted.

| # | Bước | Input | Phép tính | Output | File + symbol |
|---:|---|---|---|---|---|
| 1 | Load model | `assets/kr810.xml`, `configs/robot_config.json` | compile MJCF, cross-check `nq/nv/joint_order/ee_site` | `ModelContext` | `kinematics/model_loader.py::load_model_context, 97-174` |
| 2 | Joint order + operational limits | `robot_config.json` | resolve `jnt_qposadr`/`jnt_dofadr` per `joint_1..joint_7`; load `operational_{lower,upper}_rad`, `velocity_limits_rad_s` | ordered dof addresses, limit arrays | `::_resolve_joint_metadata, 78-94` |
| 3 | Nhận target + q_init | `q_initial`, `target_position`, `target_quaternion_wxyz` | quaternion→R; validate shape/finiteness/SO(3) | validated inputs, else `failure_reason="invalid_target"` | `kinematics/quaternion_utils.py::quaternion_wxyz_to_matrix`; `dls_solver.py::solve_dls_until_converged, 257-288` |
| 4 | FK hiện tại | `q` | `mj_forward` → `site_xpos`/`site_xmat` at `ee_site` | `p(q)`, `R(q)`, `quat_wxyz` | `kinematics/forward_kinematics.py::forward_kinematics, 26-57` |
| 5 | Position error | `p_d`, `p(q)` | `e_p = p_d − p(q)` | `(3,)` m | `kinematics/pose_error.py::position_error_vector, 23-29` |
| 6 | Orientation error | `R_d`, `R(q)` | `e_o = Log(R_d R(q)ᵀ)^∨` (**world/left** convention) | `(3,)` rad | `::orientation_error_vector_world, 37-43` + `rotation_utils.py::so3_log, 98-129` |
| 7 | Full pose error | `e_p`, `e_o` | concatenate | `e ∈ ℝ⁶`, world frame | `::full_pose_error, 51-60` |
| 8 | Geometric Jacobian | `q` | `mj_jacSite` on `ee_site`, restricted to resolved dof columns; `[J_v; J_ω]` | `J ∈ ℝ^{6×7}`, world frame | `kinematics/jacobian.py::geometric_jacobian_world, 22-50` |
| 9 | Singular values | `J` | `np.linalg.svd(J, compute_uv=False)` | `σ`, `σ_min`, `κ` | `kinematics/singularity_metrics.py::{singular_values 10-17, minimum_singular_value 20-22, condition_number 39-50}` |
| 10 | Adaptive damping | `σ_min`, thresholds | piecewise-quadratic schedule (§5.8) | `λ ∈ [λ_min, λ_max]` | `kinematics/adaptive_damping.py::compute_adaptive_damping, 20-49` |
| 11 | Weighted DLS system | `J`, `W`, `e`, `λ` | `A = JᵀWJ + λ²I₇`, `b = JᵀWe`; `W = diag(w_p,w_p,w_p,w_o,w_o,w_o)` | `A ∈ ℝ^{7×7}`, `b ∈ ℝ⁷` | `kinematics/dls_solver.py::dls_single_update, 161-166` |
| 12 | Giải hệ tuyến tính | `A`, `b` | `np.linalg.solve` (never `inv`); `LinAlgError` → `failure_reason="linear_solve_failure"` | `Δq ∈ ℝ⁷` | `::dls_single_update, 168-180` |
| 12b | Null-space centering (optional) | `q`, limits | `Δq += k·(I − J⁺J)·z`, `z = −(q−center)/half_range²`, `J⁺ = pinv(J)` | modified `Δq` | `::dls_single_update, 182-188`; `joint_limit_utils.py::joint_centering_gradient, 89-102` |
| 13 | Step clamp | `Δq`, `step_scale`, `max_joint_step_rad` | `Δq ← step_scale·Δq`; `Δq ← clip(Δq, ±max_joint_step_rad)` (element-wise) | bounded `Δq` | `::dls_single_update, 190-195` |
| 14 | Cập nhật q | `q`, `Δq` | `q_candidate = q + Δq` | candidate | `::dls_single_update, 197` |
| 15 | Limit handling | `q_candidate`, limits | if violation and `clip_to_operational_limits=False` → fail `joint_limit_failure` (q unchanged); else `np.clip` into limits | `q_next` | `::dls_single_update, 211-227`; `joint_limit_utils.py::clip_to_operational_limits, 50-53` |
| 16 | Convergence check | achieved errors | `pos_err ≤ position_success_threshold_m` **and** `orient_err_deg ≤ orientation_success_threshold_deg`; also checked **before** iteration 1 (0-iteration success) | `success` | `dls_solver.py::solve_dls_until_converged, 308, 364` |
| 16b | Stagnation check | weighted-error history | over a 5-step window, improvement `< 1e-3·max(old,1e-9)` → `failure_reason="stagnation"` | early stop | `::solve_dls_until_converged, 45-46, 368-374` |
| 17 | Success/failure class | loop exit | `success=True`, or `failure_reason ∈ {max_iterations, stagnation, joint_limit_failure, non_finite_jacobian, non_finite_input, linear_solve_failure, invalid_target}` | `DLSResult` | `::DLSResult, 68-85` |
| 18 | Iterations/runtime/errors | loop state | `time.perf_counter()` delta around the solve; last `σ_min`, `κ`, `λ`, limit margin | `DLSResult` fields | `::solve_dls_until_converged, 254, 379-395` |
| 19 | Point-IK evaluation | Tier 1 split NPZ | one independent solve per sample + initial/final `σ_min`, `κ`, margin | per-sample DataFrame | v2: `evaluation_v2/point_eval.py::evaluate_point_ik_split, 35-96`; v1: `algorithms/point_dls.py::run_point_dls, 126-175` |
| 20 | Sequential warm-start | trial `q_initial` + 400 targets | waypoint 0 from `q_initial`; waypoint *k* from waypoint *k−1*'s accepted solution; on failure recover (own finite `q_solution` → last successful `q` → trial `q_initial`); failures never stop the chain | `RawWaypointSolve[]` | `algorithms/warm_start_dls.py::run_warm_start_dls, 54-111`; `::_recover_q_initial, 41-51` |
| 21 | Sequential cold-start | same | **every** waypoint re-solved from the same fixed trial `q_initial`; no continuity, no recovery | `RawWaypointSolve[]` | `algorithms/cold_start_dls.py::run_cold_start_dls, 21-65` |
| 22 | Trial aggregation | per-waypoint frame | per `(trial_id, method)` success/completion/streak/recovery/error/runtime; paired warm-vs-cold | `trajectory_trial_summaries.csv`, `warm_vs_cold.csv` | `evaluation_v2/metrics.py::{compute_trial_summaries 93-124, compute_warm_vs_cold 135-152}` |
| 23 | Smoothness + feasibility | `q(t)` per trial | `np.gradient` vs `time_s`; joint jump/variation/jerk; limit margin, violation count, velocity utilization | `smoothness_metrics.csv`, `feasibility_metrics.csv` | `evaluation_v2/metrics.py::compute_tier4, 210-268`; `evaluation/smoothness_metrics.py::compute_smoothness_metrics, 76-137` |

Not present anywhere in the current source: line search / trust region, second-order (Newton/LM
with Jacobian of the residual w.r.t. damping), SVD-truncation pseudo-inverse IK, task-space
(`J(JᵀJ+λ²I)⁻¹`) form, quaternion-error (non-log) formulation, and any learned corrector —
**NOT IMPLEMENTED IN CURRENT SOURCE**.

## 5. Các công thức toán học và nơi cài đặt

### 5.1 Forward kinematics
\[
T_{ee}(q) = \begin{bmatrix} R(q) & p(q)\\ 0 & 1\end{bmatrix},\qquad
p(q)=\texttt{data.site\_xpos}[ee],\; R(q)=\texttt{data.site\_xmat}[ee]
\]
World frame; end-effector = MuJoCo **site** `ee_site` on body `end_effector` (not a calibrated
TCP). No TCP offset is ever added.
Implementation: `kinematics/forward_kinematics.py::forward_kinematics` — Lines `26-57`.

### 5.2 Position error
\[ e_p = p_d - p(q) \in \mathbb{R}^3\ \text{(m)} \]
Implementation: `kinematics/pose_error.py::position_error_vector` — Lines `23-29`.

### 5.3 Orientation error
\[ e_o = \operatorname{Log}\!\left(R_d\,R(q)^{\top}\right)^{\vee} \in \mathbb{R}^3\ \text{(rad)} \]
**World/left convention**, deliberately matched to the world-frame Jacobian; the body/right form
`Log(RᵀR_d)` is explicitly rejected by the module docstring.
Implementation: `kinematics/pose_error.py::orientation_error_vector_world` — Lines `37-43`;
`kinematics/rotation_utils.py::so3_log` — Lines `98-129` (θ→0 antisymmetric branch, θ→π symmetric
branch, `arccos` clamped).

Reported orientation *magnitude* uses the geodesic angle
\(\theta = \arccos\!\big((\operatorname{tr}(R_1^\top R_2)-1)/2\big)\):
`kinematics/rotation_utils.py::rotation_geodesic_angle` — Lines `132-140`.

### 5.4 Full pose error
\[ e = \begin{bmatrix} e_p \\ e_o \end{bmatrix} \in \mathbb{R}^{6},\quad
\text{order } [x,y,z,r_x,r_y,r_z],\ \text{world frame} \]
Implementation: `kinematics/pose_error.py::full_pose_error` — Lines `51-60`.
Weighted variant `w ⊙ e` (blocks 1–3 = `position_weight`, 4–6 = `orientation_weight`, no implicit
unit mixing): `::weighted_pose_error` — Lines `63-77`.

### 5.5 Jacobian
\[ \dot{x} = J(q)\,\dot q,\qquad J(q) = \begin{bmatrix} J_v \\ J_\omega\end{bmatrix}\in\mathbb{R}^{6\times 7} \]
Rows 1–3 linear, rows 4–6 angular; **world (space) frame**; columns ordered by the resolved dof
addresses of `joint_1…joint_7`. Analytical source = `mujoco.mj_jacSite`.
Implementation: `kinematics/jacobian.py::geometric_jacobian_world` — Lines `22-50`.

Finite-difference validation (central difference; orientation columns use
\(\operatorname{Log}(R_+R_-^{\top})/2\epsilon\), never Euler/quaternion differencing):
`::finite_difference_jacobian_world` — Lines `53-97`, default `ε = 1e-6` rad.

Relative error gate metric:
\[ \varepsilon_{rel} = \frac{\lVert J_{analytic}-J_{fd}\rVert_F}{\max(\lVert J_{fd}\rVert_F, 10^{-12})} \]
`::jacobian_relative_error` — Lines `100-117`.

### 5.6 DLS objective
\[
\min_{\Delta q}\ \big\lVert W^{1/2}\,(J\,\Delta q - e)\big\rVert_2^2 \;+\; \lambda^2\,\lVert \Delta q\rVert_2^2
\]
Stated verbatim in the module docstring.
Implementation: `kinematics/dls_solver.py` (module docstring lines `1-15`; realized at
`::dls_single_update` Lines `161-169`).

### 5.7 DLS linear system (joint-space normal-equation form)
\[
\big(J^{\top} W J + \lambda^2 I_7\big)\,\Delta q \;=\; J^{\top} W e
\]
- Solved with **`np.linalg.solve`** — never `np.linalg.inv`, never `lstsq`, never a task-space
  `Jᵀ(JJᵀ+λ²I)⁻¹` form.
- Dimensions: `A ∈ ℝ^{7×7}`, `b ∈ ℝ⁷`, `J ∈ ℝ^{6×7}`, `W = diag(w_p,w_p,w_p,w_o,w_o,w_o) ∈ ℝ^{6×6}`.
- Damping placement: `λ²I` on the **joint-space** (7×7) side.
- Weight placement: `W` **inside** both `JᵀWJ` and `JᵀWe` (task space).
- Pseudo-inverse `np.linalg.pinv(J)` appears **only** in the optional null-space projector, never
  in the primary solve.
Implementation: `kinematics/dls_solver.py::dls_single_update` — Lines `161-188`.

### 5.8 Adaptive damping (exact piecewise rule from code)
\[
\lambda(\sigma_{\min}) =
\begin{cases}
\lambda_{\min}, & \sigma_{\min} \ge \tau\\[4pt]
\operatorname{clip}\!\Big(\lambda_{\max}-(\lambda_{\max}-\lambda_{\min})\big(\tfrac{\sigma_{\min}}{\tau}\big)^{2},\ \lambda_{\min},\ \lambda_{\max}\Big), & \sigma_{\min} < \tau
\end{cases}
\]
with \(\tau=\) `singularity_sigma_threshold`. Continuous at `τ`, monotonically non-increasing in
`σ_min`, `λ→λ_max` as `σ_min→0`. When `damping_mode != "adaptive"`, a constant
`lambda_default` is used instead.
Implementation: `kinematics/adaptive_damping.py::compute_adaptive_damping` — Lines `20-49`;
dispatch at `kinematics/dls_solver.py::dls_single_update` Lines `151-159`.

### 5.9 Joint update
\[
\Delta q \leftarrow \operatorname{clip}\!\big(\alpha\,\Delta q,\ -\delta_{\max},\ +\delta_{\max}\big),\qquad
q_{k+1} = \Pi_{[q_{lo},q_{hi}]}\big(q_k + \Delta q\big)
\]
`α = step_scale` (config, currently 1.0); `δ_max = max_joint_step_rad` (0.1 rad); the projection
`Π` is an element-wise `np.clip` applied **only when** `clip_to_operational_limits=True` —
otherwise a violating candidate is rejected and `q` is left unchanged.
Implementation: `kinematics/dls_solver.py::dls_single_update` — Lines `190-227`.

### 5.10 Singularity metrics
\[
\sigma(J)=\mathrm{svd}(J),\quad \sigma_{\min}=\sigma_{-1},\quad
\kappa(J)=\frac{\sigma_{\max}}{\sigma_{\min}}\ \ (=\infty \text{ if } \sigma_{\min}\le 10^{-12})
\]
\[
\mathrm{rank}_{num}(J)=\#\{\sigma_i > 10^{-6}\sigma_{\max}\},\qquad
w(J)=\sqrt{\det(JJ^{\top})}\ \ \text{(Yoshikawa)},\qquad w_v = \sqrt{\det(J_vJ_v^{\top})}
\]
Implementation: `kinematics/singularity_metrics.py::{singular_values 10-17,
minimum_singular_value 20-22, maximum_singular_value 25-27, numerical_rank 30-36,
condition_number 39-50, is_near_singular 53-57}`;
`kinematics/manipulability.py::{yoshikawa_manipulability 20-31, positional_manipulability 34-45,
normalized_jacobian 48-62}`. The module documents that full-`J` Yoshikawa mixes m and rad units and
is not an absolute cross-robot metric.

### 5.11 Evaluation metrics

| Metric | Định nghĩa thực tế | Implementation |
|---|---|---|
| position error | `‖e_p‖₂` (m) | `dls_solver.py::_pose_error_components, 88-92` |
| orientation error | `‖e_o‖₂` (rad) → `np.degrees` | same, + `solve_dls_until_converged:300` |
| success (solver) | `pos ≤ thr_pos ∧ orient_deg ≤ thr_deg` | `dls_solver.py:308, 364` |
| success (reporting) | post-hoc per tier `coarse/standard/strict`, never fed back to the solver | `evaluation_v2/reporting.py::reporting_success, 14-27` |
| RMSE / mean / median / P95 / max | `√mean(x²)`, `mean`, `median`, `percentile(x,95)`, `max` | `evaluation_v2/metrics.py::_err_stats, 25-35`; `evaluation/trajectory_metrics.py::compute_position_tracking_metrics, 56-92` |
| success rate | mean of boolean `success_<tier>` per group / per trial | `evaluation_v2/metrics.py::compute_point_metrics 41-69`, `compute_trial_summaries 93-124` |
| waypoint success rate | mean `success_standard` over a trial's waypoints | `::compute_trial_summaries, 115-116` |
| iteration count / runtime | `DLSResult.iterations`, `solve_time_ms` (`perf_counter` around solve only) | `dls_solver.py:254,379`; `evaluation/runtime_metrics.py::compute_runtime_metrics, 35-62` (count, total, mean, median, std, P90/P95/P99, max, optional deadline miss rate) |
| joint step (jump) | `max_{k,j} |q_{k+1,j} − q_{k,j}|` | `evaluation/smoothness_metrics.py, 103-107` |
| joint velocity / acceleration / jerk | successive `np.gradient(·, time_s, edge_order=2)`; requires ≥2/≥3/≥4 samples else reported `unavailable` | `::compute_smoothness_metrics, 87-101` |
| total joint variation | `Σ_k |Δq_k|` per joint | `::compute_smoothness_metrics, 108` |
| second-difference norm | `√mean((q_{k+1}−2q_k+q_{k−1})²)` | `::compute_smoothness_metrics, 110-113` |
| limit margin | `min_i dist(q_i, nearest bound)/half_range_i` (normalized; <0 ⇒ violation) | `kinematics/joint_limit_utils.py::{normalized_joint_limit_margin 62-74, minimum_joint_limit_margin 77-79}` |
| velocity utilization | `max |q̇| / velocity_limits_rad_s` | `evaluation_v2/metrics.py::compute_tier4, 245` |
| warm-start improvement | paired per-trial warm vs cold on 13 metrics | `::compute_warm_vs_cold, 127-152` |
| continuity / recovery | `maximum_failure_streak`; `recovery_rate = #(fail→success)/#(fail followed by any wp)` | `::_failure_streaks 75-80`, `::_recovery_rate 83-90` |
| path deviation (cross-track) | perpendicular distance to the target polyline (`project_point_to_polyline`), + `final_progress_ratio` | `evaluation/cross_track_metrics.py::compute_cross_track_metrics, 97-…` |
| coverage / path length ratio | `actual_path_length / target_path_length`; selection uses `min(ratio,1)` | `evaluation/trajectory_metrics.py, 71-73`; `development_selection_report.json::selection_objective.levels[5]` |
| repeatability (v1 only) | ISO-9283-**inspired** accuracy/repeatability over repeated trials — *no ISO certification claimed* | `evaluation/iso9283_metrics.py::{compute_path_accuracy 39-…, compute_path_repeatability 82-…}` |
| confidence intervals | Wilson (proportions), bootstrap (means) | `evaluation/confidence_intervals.py::{wilson_confidence_interval 32-…, bootstrap_confidence_interval 77-…}` |

## 6. Tier 0 → Tier 4 hoạt động như thế nào?

Dataset v2 evaluation (the one actually executed) — `evaluation_v2/orchestrator.py::run_evaluation`:

| Tier | Câu hỏi | Input dataset | Phương pháp | Output | Metric/gate | File pipeline |
|---|---|---|---|---|---|---|
| **0** | Có tin được model/FK/Jacobian không? | `tier0_validation/*_v2.npz` (1000 FK + 1000 Jac + 600 sing) from the **dataset root** (not the public root) | FK sanity + analytic-vs-FD Jacobian + σ_min recording. **No IK, no DLS** | `tier0_kinematics/tier0_gate_summary.json` | Hard gate: 0 non-finite FK, 0 invalid SO(3), 0 non-finite Jacobian, `max ε_rel ≤ 1e-4`. Fail ⇒ Tier 1-4 `not_run` | `evaluation_v2/tier0_gate.py::run_tier0_gate`; `evaluation/kinematics_validation.py::compute_gate_result` |
| **1** | DLS giải được từng pose độc lập tới đâu? | public `tier1_point_ik/{split}.npz` (1200 dev / 1200 val / 3600 frozen) | **Calls DLS** once per sample from that sample's `q_initial` | `point_results.csv`, `point_metrics.csv`, `point_failures.csv` | success @ coarse/standard/strict, per-difficulty breakdown, iterations, runtime, limit violation. **Never gates Tier 2-4** | `evaluation_v2/point_eval.py::evaluate_point_ik_split` |
| **2** | Chuỗi waypoint có giữ được nghiệm không? | public trajectories (400 wp) + public trials (210/split) × 2 methods | **Calls DLS** 400× per (trial, method). warm vs cold differ **only** in each waypoint's initial `q` | `waypoint_results.csv`, `trajectory_trial_summaries.csv`, `warm_vs_cold.csv` | per-waypoint success, completion, failure streak, recovery rate, σ_min min, margin min | `evaluation_v2/trajectory_eval.py::evaluate_trajectory_trial` + `algorithms/{warm_start,cold_start}_dls.py` |
| **3** | Quỹ đạo Cartesian bám tới đâu? | Tier 2's `waypoint_df` only | **Pure post-processing, no solver call** | `trajectory_metrics.csv`, `tracking_summary.json` | position RMSE/median/P95/max, endpoint & start error, path length ratio, orientation RMSE/P95/max, cross-track RMSE/P95/max, `final_progress_ratio` | `evaluation_v2/metrics.py::compute_tracking, 158-204` |
| **4** | Quỹ đạo khớp có mượt và khả thi động học không? | Tier 2's `waypoint_df` + `ModelContext` limits | **Pure post-processing, no solver call** | `smoothness_metrics.csv`, `feasibility_metrics.csv`, `runtime_metrics.csv` | max joint jump, total variation, global RMS jerk, max |v|/|a|/|jerk|, min limit margin, violation count, min σ_min, velocity utilization; `acceleration_status = "unavailable_no_locked_acceleration_limits"` | `evaluation_v2/metrics.py::compute_tier4, 210-268` |

**Tier nào thực sự gọi DLS:** only Tier 1 and Tier 2. Tier 0 calls FK/Jacobian only; Tier 3 and
Tier 4 are deterministic functions of Tier 2's already-solved rows (docstring of
`evaluation_v2/metrics.py`: "Tier 3 and Tier 4 never invoke a solver").

**Warm vs cold — the exact difference:** identical target sequence, trial, candidate config,
iteration cap and tolerance; the *only* difference is the per-waypoint seed configuration —
warm uses waypoint *k−1*'s accepted solution (with a 3-level recovery policy on failure), cold
always re-uses the trial's fixed `q_initial`
(`evaluation_v2/trajectory_eval.py` docstring lines 7-17; `algorithms/warm_start_dls.py:88-109`
vs `algorithms/cold_start_dls.py:52-63`).

**Dataset v1's own pipeline** (`pipelines/run_tier0_to_tier4.py`) implements the same tier
sequence with the same Tier 0 gate semantics (README lines 70-77) but has **never been executed**
on the full preset.

## 7. Cấu hình và ngưỡng quan trọng

| Tham số | Giá trị | Ý nghĩa | File + key | Hard-coded hay config |
|---|---:|---|---|---|
| position success threshold (v1 solver) | 0.006 m | DLS early stop | `configs/dls_config.json::position_success_threshold_m` | config |
| orientation success threshold (v1 solver) | 10.0° | DLS early stop | `configs/dls_config.json::orientation_success_threshold_deg` | config |
| position/orientation weight | 1.0 / 0.2 | `W` blocks | `configs/dls_config.json`; also `evaluation_v2/candidate_configs.py::_COMMON_MECHANICS` | config + code constant |
| max_iterations (v1) | 100 | iteration cap | `configs/dls_config.json::max_iterations` | config |
| lambda_min / lambda_max / lambda_default | 1e-4 / 0.2 / 0.01 | damping bounds | `configs/dls_config.json` | config |
| singularity_sigma_threshold | 0.03 | `τ` in damping + near-singular label | `configs/dls_config.json::singularity_sigma_threshold` (reused by v2 `difficulty_thresholds.json`, Tier 0 v2, anchors) | config, shared |
| step_scale | 1.0 | `α` | `configs/dls_config.json::step_scale` | config |
| max_joint_step_rad | 0.1 | per-joint `Δq` clamp | `configs/dls_config.json::max_joint_step_rad` | config |
| joint_limit_avoidance / null_space_gain (v1) | true / 0.02 | null-space centering | `configs/dls_config.json` | config |
| clip_to_operational_limits | true | projection into limits | `configs/dls_config.json` | config |
| stagnation window / min relative improvement | 5 / 1e-3 | early-stop rule | `kinematics/dls_solver.py::_STAGNATION_WINDOW`, `_STAGNATION_MIN_RELATIVE_IMPROVEMENT` | **hard-coded** |
| condition-number safe floor | 1e-12 | `κ = ∞` guard | `kinematics/singularity_metrics.py::condition_number(safe_floor)` | **hard-coded default** |
| numerical rank tolerance | 1e-6 | rank counting | `kinematics/singularity_metrics.py::_DEFAULT_RANK_TOL` | **hard-coded** |
| FD epsilon | 1e-6 rad | Jacobian FD | `kinematics/jacobian.py::_DEFAULT_FD_EPSILON_RAD`; `configs/benchmark_config.json::finite_difference_epsilon`; v2 `tier0_config.json` | hard-coded default + config |
| Jacobian relative-error gate | 1e-4 | Tier 0 hard gate | `evaluation/kinematics_validation.py::DEFAULT_JACOBIAN_RELATIVE_ERROR_THRESHOLD`; re-exported `evaluation_v2/tier0_gate.py::JACOBIAN_RELATIVE_ERROR_GATE` | **hard-coded** |
| rotation validity tolerance | 1e-6 | SO(3) check | `kinematics/rotation_utils.py::validate_rotation_matrix(tol)`; `evaluation/kinematics_validation.py::DEFAULT_ROTATION_TOLERANCE` | hard-coded default |
| **v2 reporting tiers** | coarse 6 mm/5°, standard 3 mm/2° (primary), strict 1 mm/1° | post-hoc success classes | `evaluation_v2/candidate_configs.py::REPORTING_THRESHOLDS, 39-43` | **hard-coded (pre-registered)** |
| **v2 solver convergence** | 1 mm / 1° | solver early stop for every candidate | `evaluation_v2/candidate_configs.py::CONVERGENCE_POSITION_M/_ORIENTATION_DEG, 49-50` | hard-coded (pre-registered) |
| v2 selected candidate | `cand_D_pure_dls`: 300 iters, adaptive, λ_max 0.2, clip ON, null-space **OFF** (gain 0.0) | locked evaluation config | `KR810_Tier0_Tier4_Dataset_v2.0.0/evaluation_protocol.json` | locked artifact |
| **v2 generation tolerance** | 1e-4 m / 0.01° | strict independent-FK reachability acceptance (explicitly *not* a reporting threshold) | `mpdik_kassow_v2_work/configs/generation_reachability_config.json::position_reconstruction_tolerance_m / orientation_reconstruction_tolerance_deg` | config |
| v2 generation solver | 400 iters, `pos 5e-5 m`, `orient 0.005°`, λ∈[1e-6,0.05], both weights 1.0, no null-space | generation-time IK engine only, **never a baseline result** | same file, `generation_solver` | config |
| v1 evaluation acceptance | RMSE 4 mm, P95 6 mm, max 10 mm, orientation P95 10°, min waypoint success 0.95, trajectory completion 1.0 | project-defined criteria (**not** ISO 9283) | `configs/evaluation_config.json` | config |
| v2 evaluation acceptance | `status: "not_yet_defined"` | deliberately absent; only structural acceptance is used | `mpdik_kassow_v2_work/configs/evaluation_defaults.json`; `known_limitations.md` bullet 1 | config (empty by policy) |
| near-limit threshold (v2) | 0.024991237796029034 (normalized, P10) | `near_joint_limit` group + `near_limit` anchor | `configs/difficulty_thresholds.json::near_joint_limit.threshold_normalized` | config |
| near-singular threshold (v2) | σ_min ≤ 0.03 | `near_singularity` group + `near_singular` anchor | `configs/difficulty_thresholds.json::near_singularity.threshold_sigma_min` | config |
| moderately-conditioned upper bound | σ_min 0.09 (= 3.0 × 0.03) | `regular` anchor floor | `configs/difficulty_thresholds.json::moderately_conditioned.upper_bound_sigma_min` | config |
| v1 near-singular anchor ratio | `ANCHOR_SIGMA_RATIO = 3.0` | v1 anchor predicate | `generators/_trajectory_common.py:87` | **hard-coded** |
| trajectory waypoints | 400 canonical (v1 and v2) | canonical resolution | `configs/trajectory_config.json::default_waypoints`; v2 spec §B | config |
| source resolution (v2) | core 2001 nominal, challenge 1201 | high-res source | spec §H, §I.1; `configs/trajectory_config.json`, `random_challenge_config.json` | config |
| v1 speed scales | 0.5 / 1.0 / 1.5 | trial timing only (geometry unchanged) | `configs/trajectory_config.json::speed_scales` | config |
| v1 repeatability/robustness counts | 10 repeats / 5 initial configs | v1 trial construction | `generators/_trajectory_common.py:82-83` | **hard-coded** |
| v2 trial difficulty bands | easy ≤ 0.8601; medium 0.9245–1.0462; hard ≥ 1.1127; min separation 0.0644 | init-class assignment | `mpdik_kassow_v2_work/configs/trial_config.json::difficulty.bands` | config (calibrated on development only) |
| v2 trial metric scales | pos 0.93567 m, orient 2.30143 rad, 50/50 weights | metric normalization | same file | config |
| v2 candidate pool per trajectory | 500 + 300 + 300 + 300 = 1400 | `q_initial` candidates | `trial_config.json::candidate_pool_policy` | config |
| v1 seed | 42 | v1 generation | `configs/benchmark_config.json::random_seed` | config |
| v2 master seed | 42 | all v2 generation | `mpdik_kassow_v2_work/configs/seed_policy.json::master_seed` | config |
| v2 frozen seed revisions | core 4, challenge 1, trial 1 | separate frozen namespaces | `seed_policy.json` | config |
| v1 point-IK pool | 30,000 | candidate pool | `benchmarks/point_ik/difficulty_definition.json::generic_pool_size` | generated metadata |
| v2 point-IK pool | 150,000 | candidate pool | `configs/point_ik_config.json::pair_pool_policy.pool_size_default` | config |
| operational joint limits | J1,J3,J5,J6,J7 ±2π; J2,J4 [−1.2217, +3.1416] rad | sampling + solver bounds (documented as *operational*, not verified mechanical hard stops) | `configs/robot_config.json::operational_{lower,upper}_rad`; caveat in `kinematics/joint_limit_utils.py` docstring | config |
| velocity limits | 3.9269908 rad/s × 7 | Tier 4 utilization only | `configs/robot_config.json::velocity_limits_rad_s` | config |
| acceleration limits | none | Tier 4 acceleration is descriptive only | `evaluation_v2/metrics.py:252-254` | absent by design |

## 8. Input và output thực tế của pipeline

### 8.1 Input
- **Robot asset/model**: `assets/kr810.xml` (+ `assets/kr810.urdf`, `assets/meshes/a810/*.stl`),
  resolved via `kinematics/model_loader.py::DEFAULT_MODEL_PATH`.
- **`q_initial`**: Tier 1 — `tier1_point_ik/{split}.npz::q_initial`; Tier 2 — `trials/{split}.npz::q_initial`.
- **Target position/orientation**: `target_position`, `target_quaternion_wxyz` (Tier 1);
  `target_position`, `target_quaternion` (Tier 2 canonical trajectory NPZ).
- **Trajectory waypoints**: 400 canonical rows + `time_s`, `cumulative_arc_length_m`,
  `cumulative_angular_displacement_rad` per trajectory.
- **Trial metadata**: `trial_id`, `trajectory_id`, `trajectory_family`, `difficulty`, `content_hash`.
- **DLS config**: `CandidateConfig.solver_config()` (v2) or `configs/dls_config.json` (v1).
- **Evaluation config**: `evaluation_v2/candidate_configs.py` reporting tiers (v2);
  `configs/evaluation_config.json` (v1).

### 8.2 Output (per run directory)

| Output file | Producer | Consumer | Key columns/fields |
|---|---|---|---|
| `tier0_kinematics/tier0_gate_summary.json` | `evaluation_v2/tier0_gate.py::run_tier0_gate` | orchestrator gate | `gate_pass`, `max_jacobian_relative_error`, `reasons`, `minimum_sigma_min` |
| `tier1_point_dls/point_results.csv` | `point_eval.py::evaluate_point_ik_split` | `compute_point_metrics`, selection | `sample_id, difficulty_id, converged, position_error_m, orientation_error_deg, iterations, solve_time_ms, initial/final_sigma_min, final_condition_number, minimum_joint_limit_margin, joint_limit_violation, failure_reason, success_{coarse,standard,strict}, q_solution_q1..q7` |
| `tier1_point_dls/point_metrics.csv`, `point_failures.csv` | `metrics.py::compute_point_metrics` | report | per-group success rates + error/iteration/runtime stats |
| `tier2_sequential_dls/waypoint_results.csv` | `trajectory_eval.py::evaluate_trajectory_trial` | Tier 2/3/4 aggregation | above + `trial_id, trajectory_id, method, waypoint_id, time_s, target/actual position & quaternion, sigma_min, condition_number, manipulability, recovered_after_previous_failure` |
| `tier2_sequential_dls/trajectory_trial_summaries.csv` | `compute_trial_summaries` | warm-vs-cold, selection | `waypoint_count, full_trajectory_completed, converged_rate, maximum_failure_streak, recovery_rate, success_rate_*, *_rmse/p95/max, minimum_sigma_min` |
| `tier2_sequential_dls/warm_vs_cold.csv` | `compute_warm_vs_cold` | analysis | 13 paired `warm_*`/`cold_*` metrics per trial |
| `tier3_trajectory_tracking/{trajectory_metrics.csv, tracking_summary.json}` | `compute_tracking` | report | position RMSE/P95/max, endpoint/start error, path_length_ratio, orientation RMSE/P95/max, cross-track RMSE/P95/max, `final_progress_ratio`, `coverage_ratio` |
| `tier4_joint_feasibility/{smoothness,feasibility,runtime}_metrics.csv` | `compute_tier4` | report | `max_joint_jump_rad, total_joint_variation_rad, global_rms_jerk, max_abs_{velocity,acceleration,jerk}`; `minimum_joint_limit_margin_rad, operational_limit_violation_count, minimum_sigma_min, maximum_velocity_utilization, acceleration_status`; `mean/median/p90/p95/p99/max_ms` |
| `run_manifest.json` | orchestrator | provenance | per-tier status, fingerprints, environment |
| `resolved_config.json` | orchestrator | reproducibility / frozen audit | candidate record, splits, methods, limits |
| `FINAL_SUMMARY.json` | orchestrator | selection input | point success rate, waypoint count, tracking summary |
| `checkpoint/{run_lock.json, shard_index.json, shards/*.csv}` | `evaluation_v2/checkpoint.py` | resume | 421 shards per run, verified 0 corrupted |
| `development_selection_report.json` | `evaluation_v2/selection.py` | candidate lock | lexicographic `selection_levels` + full ranking |
| `evaluation_lock_bundle.json` | `evaluation_v2/lock_bundle.py` | frozen precondition | 6 fingerprints + locked candidate |
| `frozen_access_ledger.json` / `frozen_access_report.json` | `evaluation_v2/frozen_ledger.py` | frozen governance | `access_count = 1`, `run_id`, `no_retune_confirmation` |
| `final_dls_summary.json` | `evaluation_v2/release_builder.py` | **the DLS baseline result** | per-split point-IK, warm/cold, error tails, failures, runtime, solve counts |
| `CHECKSUM_MANIFEST.json`, `SHA256SUMS.txt`, 3 release ZIPs | `release_packaging.py`, `pipelines/build_dataset_v2_release.py` | distribution | integrity |
| Plots (`figures/`) | `evaluation/plotting.py` | v1 pipeline only | CDF/histogram/3D tracking/warm-vs-cold |

## 9. DLS hiện giải quyết tốt gì và còn hạn chế gì?

### Đã được chứng minh

| Kết luận | Bằng chứng |
|---|---|
| Model loads and matches config (nq=nv=7, joint order, `ee_site` present) | `tests/test_model_dimensions.py`, `tests/test_asset_loading.py` |
| FK is finite, orthogonal, unit-quaternion, deterministic, matches raw MuJoCo site pose | `tests/test_forward_kinematics.py` (11 tests); Tier 0 gate `validate_fk_states` |
| Analytic Jacobian matches central finite difference | `tests/test_jacobian.py::test_geometric_jacobian_matches_finite_difference`; **Tier 0 gate passed on dev, validation and frozen runs** (`PHASE_8A_FINAL_SUMMARY.json::tier0_gate`, frozen `run_manifest.json::tiers.tier0.gate_pass`) with `max ε_rel ≤ 1e-4` |
| SO(3) log/exp stable at θ→0 and θ→π; orientation error norm = geodesic angle; quaternion sign-invariant | `tests/test_rotation_utils.py`, `tests/test_pose_error.py` |
| Damping increases near singularities and output stays finite | `tests/test_dls_solver.py::test_near_singular_configuration_increases_damping_and_stays_finite` |
| Step clamp and limit clipping actually engage / can be disabled | `tests/test_dls_solver.py::{test_max_joint_step_is_respected_for_large_pose_error, test_clip_to_operational_limits_engages_and_can_be_disabled}` |
| `q_target`/`q_reference` never used as an initial guess | `tests/test_point_dls_algorithm.py::test_q_target_is_not_used_as_initial_guess`; `tests/test_dataset_v2_eval_harness.py::test_public_qinitial_never_equals_reference_solution` |
| Public export carries no protected reference array | `tests/test_dataset_v2_eval_harness.py` (3 isolation tests) + runtime guard `evaluation_v2/protected_guard.py` |
| v2 seeds are NumPy-version-independent and reproducible | `tests/test_dataset_v2_seed_determinism.py` (17 tests, golden vectors) |
| Anti-leakage across the 3 splits on all 7 dimensions | `configs/split_policy.json::anti_leakage_dimensions`; `*_anti_leakage_report.json` per component |
| Targets are reachable **by construction** (independent FK check at 1e-4 m / 0.01°, every canonical and source waypoint) | `configs/generation_reachability_config.json::acceptance_rule`; `*_reachability_report.json` |
| Point-IK DLS is strong: standard-tier success **0.963 dev / 0.963 val / 0.951 frozen**; position P95 ≈ 1.0/1.0/1.9 mm | `final_dls_summary.json::*.point_ik` |
| Execution safety: **0 non-finite** out of 171,600 frozen solves; 100% trajectory completion on all splits | `final_dls_summary.json::*.failures.non_finite_count`, `*.completion_and_coverage.completion_macro` |
| Full run really was full (no smoke shortcut) | `frozen_access_report.json::exact_workload` = 3,600 point + 168,000 waypoint = 171,600 |
| Frozen protocol respected: one access, config byte-identical to the pre-frozen lock | `frozen_access_report.json::{frozen_access_count: 1, no_retune_confirmation}` |

### Đang được benchmark nhưng chưa thể kết luận

- **No numeric performance acceptance threshold exists for v2** — `quantitative_performance_acceptance_status = not_defined` by design (`known_limitations.md`), so "pass/fail" of the baseline's accuracy is *undefined*, only structural acceptance passed. The v1 thresholds (4 mm RMSE etc.) belong to the v1 pipeline that was never run and were **not** applied to v2.
- Per-difficulty-group and per-family breakdowns exist in `point_metrics.csv` / `trajectory_trial_summaries.csv` but are **not summarized** in `final_dls_summary.json`; near-singularity vs near-limit performance therefore has data but no published aggregate here.
- Warm-start improvement magnitude varies strongly across splits (warm−cold standard = +0.177 dev, +0.262 val, +0.220 frozen); the recovery rate differs 2× between dev (0.119) and validation (0.256) — direction is consistent, magnitude is not stable.
- Runtime: P50 4–7 ms, P95 35–56 ms, P99 127–209 ms, max 330–512 ms per solve. No real-time deadline is configured (`deadline_ms=None` in `compute_tier4`), so no real-time claim is supported.
- Cross-track / path-deviation and ISO-9283-inspired numbers are computed but not aggregated into the released summary.

### Chưa nằm trong phạm vi hiện tại
Dynamics, torque, actuators (`nu=0`), controllers, collision, calibrated TCP, physical-robot
accuracy, ISO 9283 certification, and any MPDIK / PPO / MAPPO comparison — none exist in
`algorithms/`, `evaluation/`, `evaluation_v2/`, or `pipelines/`.

## 10. Vấn đề mà MPDIK cần giải quyết sau này

| DLS failure signal | Ý nghĩa | Dữ liệu chứng minh | MPDIK sau này phải cải thiện metric nào |
|---|---|---|---|
| Sequential success collapses vs point-IK: standard-tier **0.549 warm / 0.329 cold** on frozen vs **0.951** point-IK | The solver can hit a *single* pose but cannot hold accuracy along a 400-waypoint chain | `final_dls_summary.json::frozen_test.{point_ik.success_standard, warm_start/cold_start.trial_macro_success_standard}` | `waypoint_success_standard` (warm and cold reported separately) |
| **Stagnation dominates**: 93,765 stagnation vs 1,952 max_iterations (frozen); 88,219/1,083 (dev) | The failure mode is a *descent* failure (weighted error stops improving inside the 5-step window), not an iteration-budget failure — a deeper budget alone will not fix it (candidates B–E with 300 iters did not) | `final_dls_summary.json::*.failures.failure_reason_counts`; `development_selection_report.json` ranking | fraction of solves ending in `stagnation` |
| Heavy error tail: position P95 0.85 m (dev) / 0.85 m (val, 0.92) / 0.85 m (frozen), max ≈ 1.6 m; orientation P95 ≈ 128–133°, max ≈ 180° | Failures are catastrophic, not marginal — the solver ends far from the target on a substantial minority of waypoints | `final_dls_summary.json::*.error_tails` | `position_p95_m`, `orientation_p95_deg`, `*_max` |
| Cold-start ≪ warm-start on every split | Strong dependence on initial configuration — exactly the redundancy-resolution weakness | `final_dls_summary.json::*.{warm_start,cold_start}.trial_macro_success_standard` | `trajectory_standard_cold`, and the warm−cold gap |
| Low continuity recovery: warm `recovery_rate_mean` 0.119 dev / 0.256 val / 0.125 frozen | After a waypoint fails, warm-start rarely recovers on the next waypoint ⇒ long failure streaks | `final_dls_summary.json::*.warm_start.recovery_rate_mean`; per-trial `maximum_failure_streak` in `trajectory_trial_summaries.csv` | `recovery_rate`, `maximum_failure_streak` |
| Coverage < 1 despite 100% completion: `coverage_macro` 0.970 / 0.953 / 0.963 | Every trial runs all 400 waypoints, but the realized path is ~3–5% shorter than commanded ⇒ systematic path shortcutting | `final_dls_summary.json::*.completion_and_coverage` | `coverage_ratio`, `cross_track_rmse_m` |
| Runtime tail: P99 127–209 ms, max 330–512 ms per solve | Iterating harder near hard poses costs wall-clock time; a learned corrector's value proposition includes bounded inference cost | `final_dls_summary.json::*.runtime` | `runtime_p99` (must not regress) |
| Null-space centering did **not** help | The selected candidate `cand_D_pure_dls` has `joint_limit_avoidance=False`, i.e. the hand-designed redundancy-resolution term was measurably not the winner | `development_selection_report.json::ranking`; `evaluation_protocol.json` | joint-limit margin + success jointly, i.e. redundancy resolution must be *learned*, not hand-weighted |
| Near-singular / near-limit specific degradation | Data exists (`difficulty_id` groups 4/5, challenge families `near_limit_region`/`near_singular_region`, per-trial `minimum_sigma_min`) but no aggregate was published | `point_metrics.csv`, `trajectory_trial_summaries.csv` in each run dir | **HYPOTHESIS — REQUIRES A PER-GROUP AGGREGATION PASS OVER THE EXISTING RESULT CSVs** (data already exists; the number does not) |
| Joint jump / discontinuity magnitude | `max_joint_jump_rad`, `global_rms_jerk`, `total_joint_variation_rad` are computed per (trial, method) in Tier 4 but are not in the released summary | `tier4_joint_feasibility/smoothness_metrics.csv` | **HYPOTHESIS — REQUIRES AGGREGATION OF EXISTING TIER 4 OUTPUT** |
| Joint-limit violation rate | Column exists (`joint_limit_violation`, `operational_limit_violation_count`) and clipping is ON, so violations are expected to be 0 | `point_results.csv`, `feasibility_metrics.csv` | **HYPOTHESIS — NOT AGGREGATED IN THE RELEASED SUMMARY** |

**Fairness constraint for any future comparison:** the locked evaluation config
(`evaluation_protocol.json`), the same public splits, the same post-hoc reporting tiers, and the
one-shot frozen-test protocol (`configs/split_policy.json::frozen_test_protocol`) must be reused
unchanged. No claim that MPDIK is better or worse than DLS is supported by anything currently in
this tree.

## 11. End-to-end map

```
[dataset root  mpdik_kassow_v2_work]            [public export  mpdik_kassow_v2_eval_public(_frozen)]
 tier0_validation/*.npz ──────┐                  tier1_point_ik/{split}.npz   trials/{split}.npz
 configs/*.json               │                  trajectories/{split}/*.npz   public_trajectory_manifest.csv
                              v                                  │
                    [TIER 0 GATE]  evaluation_v2/tier0_gate.py    │  (protected keys stripped:
              FK sanity + analytic-vs-FD Jacobian (eps_rel<=1e-4) │   q_reference, q_target_reference, ...)
                    evaluation/kinematics_validation.py           │
                              │ pass                              v
                              └──────────────> [q_initial, target_position, target_quaternion]
                                                          │
                       kinematics/model_loader.py::load_model_context  (assets/kr810.xml, ee_site)
                                                          v
                    FK  kinematics/forward_kinematics.py::forward_kinematics   -> p(q), R(q)
                                                          v
       POSE ERROR  kinematics/pose_error.py::full_pose_error   e=[p_d-p ; Log(R_d R^T)^v]  (world, R^6)
                                                          v
       JACOBIAN/SVD  kinematics/jacobian.py::geometric_jacobian_world (6x7, world)
                     kinematics/singularity_metrics.py -> sigma_min, kappa
                                                          v
       ADAPTIVE DAMPING  kinematics/adaptive_damping.py::compute_adaptive_damping  lambda(sigma_min)
                                                          v
       DLS SOLVE  kinematics/dls_solver.py::dls_single_update
                  (J^T W J + lambda^2 I) dq = J^T W e   [np.linalg.solve]  (+ optional (I-J+J)z)
                                                          v
       JOINT UPDATE  dq <- clip(alpha*dq, +-0.1 rad);  q <- clip(q+dq, limits)
                                                          v
       CONVERGENCE  solve_dls_until_converged: pos<=thr & orient<=thr | stagnation(5,1e-3) | max_iter
                                                          v
   ┌──────────────────────────────┴───────────────────────────────┐
   v                                                              v
[TIER 1] evaluation_v2/point_eval.py            [TIER 2] evaluation_v2/trajectory_eval.py
 point_results.csv / point_metrics.csv           warm: algorithms/warm_start_dls.py (q from wp k-1)
 (1200 dev | 1200 val | 3600 frozen)             cold: algorithms/cold_start_dls.py (q fixed)
                                                 waypoint_results.csv -> trial summaries, warm_vs_cold
                                                              v
                       [TIER 3] evaluation_v2/metrics.py::compute_tracking   (no solver)
                        trajectory_metrics.csv: RMSE/P95/max, cross-track, coverage
                                                              v
                       [TIER 4] evaluation_v2/metrics.py::compute_tier4      (no solver)
                        smoothness / feasibility / runtime CSV
                                                              v
       SELECTION (development only)  evaluation_v2/selection.py -> cand_D_pure_dls
       LOCK  evaluation_lock_bundle.json -> FROZEN RUN (ledger, access_count=1)
                                                              v
       BASELINE EVIDENCE FOR MPDIK   KR810_Tier0_Tier4_Dataset_v2.0.0/final_dls_summary.json
```

## 12. Source index tối thiểu

| File | Vai trò | Symbol/key quan trọng |
|---|---|---|
| **Model / assets** | | |
| `assets/kr810.xml`, `assets/kr810.urdf`, `assets/meshes/a810/*.stl` | compiled MuJoCo model + source URDF + 8 meshes | body `end_effector`, site `ee_site` |
| `assets/model_metadata.json` | asset provenance + caveats | `end_effector_definition` ("NOT an officially calibrated TCP"), `known_limitations` (`nu=0`) |
| `configs/robot_config.json` | joint order, limits, velocity limits | `joint_order`, `operational_lower_rad/upper_rad`, `velocity_limits_rad_s`, `end_effector_site` |
| `configs/frame_config.json` | frame conventions | `jacobian_frame=world`, `pose_error_frame=world`, `orientation_error_type=so3_log`, `quaternion_order=wxyz` |
| **Dataset / config** | | |
| `DATASET_MANIFEST.json`, `VERSION` (repo) | Dataset v1 manifest (v1.0.0) | `generation_summary`, `acceptance_criteria`, `notes[2]` (evaluation never run) |
| `configs/{dls,evaluation,benchmark,trajectory,experiment_presets}_config.json` | v1 solver/eval/generation knobs | see §7 |
| `specs/DLS_DATASET_V2_SPEC.md` | locked v2 design | §B counts, §E seeds, §F/G/H/I/J policies, §K anti-leakage |
| `mpdik_kassow_v2_work/configs/*.json` (13) | v2 generation policy | `seed_policy`, `difficulty_thresholds`, `generation_reachability_config`, `trial_config`, `split_policy` |
| `mpdik_kassow_v2_work/DATASET_MANIFEST.json` | v2 realized counts (status field stale) | `counts.*` |
| `KR810_Tier0_Tier4_Dataset_v2.0.0/` | public v2.0.0 release | `final_dls_summary.json`, `evaluation_protocol.json`, `known_limitations.md`, `CHECKSUM_MANIFEST.json` |
| **Kinematics** | | |
| `kinematics/model_loader.py` | model + metadata resolution | `ModelContext`, `load_model_context` |
| `kinematics/forward_kinematics.py` | FK at `ee_site` | `forward_kinematics`, `FKResult` |
| `kinematics/pose_error.py` | position + SO(3)-log orientation error | `full_pose_error`, `orientation_error_vector_world`, `weighted_pose_error` |
| `kinematics/jacobian.py` | analytic + FD Jacobian | `geometric_jacobian_world`, `finite_difference_jacobian_world`, `jacobian_relative_error` |
| `kinematics/rotation_utils.py` | SO(3) log/exp, geodesic angle | `so3_log`, `so3_exp`, `rotation_geodesic_angle`, `validate_rotation_matrix` |
| `kinematics/singularity_metrics.py` / `manipulability.py` | σ, κ, rank, Yoshikawa | `minimum_singular_value`, `condition_number`, `yoshikawa_manipulability` |
| `kinematics/joint_limit_utils.py` | margins, clipping, centering gradient | `minimum_joint_limit_margin`, `clip_to_operational_limits`, `joint_centering_gradient` |
| **DLS** | | |
| `kinematics/dls_solver.py` | the solver | `dls_single_update`, `solve_dls_until_converged`, `DLSResult` |
| `kinematics/adaptive_damping.py` | λ(σ_min) schedule | `compute_adaptive_damping` |
| `algorithms/point_dls.py` | v1 Tier 1 wrapper | `run_point_dls`, `PointIKResult.q_target_reference` |
| `algorithms/warm_start_dls.py` / `cold_start_dls.py` | Tier 2 seeding strategies | `run_warm_start_dls`, `_recover_q_initial`, `run_cold_start_dls` |
| `algorithms/sequential_dls.py` | v1 trial runner | `run_sequential_trial`, `validate_trial_against_trajectory` |
| **Generation** | | |
| `generators/_common.py`, `_trajectory_common.py` | v1 seeds, anchors, trials | `derive_seed`, `select_anchor`, `build_trials`, `validate_sequential_reachability` |
| `generators/generate_point_ik_dataset.py` | v1 Tier 1 | `PRIORITY_ORDER`, `_derive_thresholds`, `_classify_pool` |
| `dataset_v2/seeds.py` | v2 deterministic seeds | `derive_seed`, `SEED_ALGORITHM_ID` |
| `dataset_v2/{tier0,point_ik,anchor,core_trajectory,challenge_trajectory,trial}_generation.py` | v2 generators | `run_*_generation`, `resample_canonical`, `greedy_farthest_point_select` |
| `dataset_v2/generation_reachability.py` | strict independent-FK acceptance | reachability acceptance rule |
| `dataset_v2/{locator,manifest,checksums,schemas}.py` | root resolution, manifests, hashes | `require_dataset_v2_root` |
| **Pipeline** | | |
| `pipelines/run_tier0_to_tier4.py` (+ per-tier CLIs) | v1 Tier 0–4 runner (never run full) | `main`, `--preset smoke\|full` |
| `pipelines/run_dataset_v2_*.py` | v2 generation/eval/release CLIs | `run_dataset_v2_evaluation`, `run_dataset_v2_frozen_confirmation`, `build_dataset_v2_release` |
| **Evaluation** | | |
| `evaluation_v2/orchestrator.py` | Tier 0→4 v2 driver | `run_evaluation(..., allow_frozen)` |
| `evaluation_v2/candidate_configs.py` | pre-registered candidates + tiers | `REPORTING_THRESHOLDS`, `candidate_set`, `CandidateConfig.solver_config` |
| `evaluation_v2/{point_eval,trajectory_eval,tier0_gate,metrics,reporting}.py` | tier evaluators + metrics | `evaluate_point_ik_split`, `evaluate_trajectory_trial`, `compute_{point_metrics,trial_summaries,warm_vs_cold,tracking,tier4}` |
| `evaluation_v2/{selection,lock_bundle,frozen_ledger,protected_guard,checkpoint,public_export,release_builder}.py` | governance + packaging | lexicographic selection, one-shot frozen access, protected-field guard |
| `evaluation/{kinematics_validation,trajectory_metrics,orientation_metrics,cross_track_metrics,smoothness_metrics,runtime_metrics,iso9283_metrics,confidence_intervals}.py` | metric math (shared by v1 and v2) | `compute_gate_result`, `compute_position_tracking_metrics`, `compute_smoothness_metrics` |
| **Validation / test** | | |
| `tests/test_{forward_kinematics,jacobian,pose_error,rotation_utils,dls_solver}.py` | kinematics + solver correctness | see §9 |
| `tests/test_{point_dls_algorithm,sequential_dls_algorithm}.py` | warm/cold semantics, no-`q_target` leak | `test_q_target_is_not_used_as_initial_guess` |
| `tests/test_dataset_v2_{eval_harness,eval_units,frozen,seed_determinism,release}.py` | isolation, thresholds, frozen ledger, determinism | `test_evaluation_never_reads_frozen_test` |
| `tests/test_{point_dataset,trajectory_files}.py` | v1 dataset integrity | checksum, FK-of-`q_target`, schema |
| **Documentation** | | |
| `CLAUDE.md`, `README.md` | project rules + v1 usage | tier definitions, out-of-scope list |
| `docs/DLS_FULL_EVALUATION_SPEC.md` | full-vs-smoke, ee_site, allowed conclusions | §A executive summary, §N MPDIK comparison requirements |
| `docs/V2_IMPLEMENTATION_LOG.md` | phase-by-phase v2 record | Phase 8A (selection/lock), Phase 8B (frozen + release) |
| `docs/V2_{THRESHOLD,TRIAL_DIFFICULTY}_CALIBRATION.md` | how thresholds/bands were derived | normalized-margin rationale, difficulty bands |
| `docs/V2_REPO_AUDIT.md` | Phase 0 audit | repo-vs-spec gaps |

---

### UNKNOWN / NOT FOUND
- Per-difficulty-group and per-trajectory-family success rates for Tier 2 (data present in the run
  CSVs, **not aggregated anywhere**) — `NOT FOUND` as a published number.
- Tier 3 cross-track and Tier 4 smoothness/feasibility aggregate values for the frozen run —
  `NOT FOUND` in `final_dls_summary.json` (per-trial CSVs exist).
- Any numeric acceptance threshold for Dataset v2 performance — `not_defined` by design.
- `reports/GENERATION_REPORT.json` at the v2 root — declared in `DATASET_MANIFEST.json::pointers`
  but the `reports/` directory contains only `.gitkeep`; the per-component generation reports live
  next to their data instead (`tier0_generation_report.json`, `point_ik_generation_report.json`, …).
- `mpdik_kassow_v2_work/trials/validation.npz` protected evidence exists for all three splits, but
  **no frozen protected evidence archive was ever generated** (stated in the Phase 8B log).
