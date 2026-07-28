# SR-PPO-DLS Reference Requirements

Source: `docs/srpdik/references/SR_PPO_DLS_KR810_Theory_and_Dataset_Application.pdf`
(SHA256 `b9a9fe0c65719ccbcfb7cf92bbea4b72b016d6a1c43f91892614bdfad0c96395`, 20 pages, text layer
extracted verbatim to the sibling `.txt` file — no OCR used).

Naming override: the PDF's own proposed package name is `sr_ppo_dls/` under `mpdik_kassow/`
(PDF section 12, page 16). Per direct user instruction this project uses **`srpdik`** as the
name for every new package/directory/file instead. The "planned file" column below substitutes
`srpdik/...` for the PDF's `mpdik_kassow/sr_ppo_dls/...` paths. This substitution is a project
decision, not something the PDF states — see `docs/srpdik/DECISIONS.md`.

Legend: **REQUIRED** = must be implemented for SR-PPO-DLS to match the locked design.
**OPTIONAL** = PDF frames it as tunable/ablation/nice-to-have. **OUT_OF_SCOPE** = PDF or
CLAUDE.md explicitly excludes it.

---

## 1. Research objective

- PDF: §1 "Tóm tắt điều hành", p.1. Core claim: locked DLS (`cand_D_pure_dls`) already gets
  ~95.08% standard Point-IK success on frozen-test, but trajectory standard success drops to
  ~54.93% (warm-start) / ~32.92% (cold-start) because DLS is sensitive to initial seed/basin
  choice, not a numerical-safety failure (0 non-finite over 171,600 frozen solves). Goal: a PPO
  policy that proposes a bounded residual correction to `q_initial`, producing a better seed for
  the same locked DLS solver — not a replacement IK method.
- Hypotheses (p.2, eq. 4-6): H1 success gain, H2 stagnation reduction, H3 degradation rate ≈ 0.
- Planned file: `docs/srpdik/SRPDIK_IMPLEMENTATION_PLAN.md` (restates goal/hypotheses as
  acceptance criteria); no code module (this is a framing section).
- Status: **REQUIRED** (defines what "success" means for every later module).

## 2. Overall architecture

- PDF: §6.1 "Sơ đồ tổng thể", p.6 (Figure 1) and §15 "Kết luận thiết kế", p.18-19 (final
  pipeline: `q_initial → PPO bounded residual → q_proj → safety accept/fallback → q_seed →
  locked DLS → q_solution`).
- Planned files: `srpdik/envs/kr810_sr_ppo_dls_env.py` (orchestrates the pipeline per episode);
  `srpdik/sr_ppo_dls/{observation,residual_action,safety_filter,paired_reward,baseline_cache,
  fingerprints}.py` (per-stage modules, PDF §12, p.16).
- Status: **REQUIRED**.

## 3. Observation, 36-D

- PDF: §6.3 "Observation 36 chiều", p.7 (eq. 33, field table). Composition: normalized joint
  state (7), normalized position error (3), normalized orientation error (3), lower joint-limit
  margins (7), upper joint-limit margins (7), normalized min singular value (1), normalized
  log-condition-number (1), DLS probe direction normalized by max joint step (7) = 36.
- Forbidden fields (p.7, "Các field bị cấm"): `q_target_reference`, `q_reference`,
  `waypoint_reachable`, any future joint solution, or protected conditioning fields — using them
  is leakage and invalidates comparison to DLS.
- Planned file: `srpdik/sr_ppo_dls/observation.py`; reuses `kinematics/joint_limit_utils.py`
  (margins), `kinematics/singularity_metrics.py` (σ_min, condition number),
  `kinematics/pose_error.py` (position/orientation error), `kinematics/dls_solver.py::
  dls_single_update` (probe, §6.4, p.7, eq. 34 — probe is a feature only, never applied
  directly).
- Status: **REQUIRED**. Field exclusion list is **REQUIRED** and directly testable
  (`test_sr_ppo_no_protected_fields.py`, PDF p.16).

## 4. Action residual, 7-D

- PDF: §6.5 "Action residual", p.7-8 (eq. 35-38). Actor outputs normalized `a ∈ [-1,1]^7`;
  per-joint residual `Δq_j = α_j (q_j,max − q_j,min) a_j`; candidate seed
  `q_cand = q_initial + Δq_PPO`. `a = 0 ⇒ q_cand = q_initial` is a hard do-no-harm invariant.
  `α_j` initially shared as scalar `α` (tunable, §14.4, p.18).
- Planned file: `srpdik/sr_ppo_dls/residual_action.py`.
- Status: **REQUIRED**.

## 5. Seed projection (safe joint range)

- PDF: §6.6 "Projection vào safe joint range", p.8 (eq. 39). Per-joint clamp with margin
  `δ_j ≥ 0`: `q_proj,j = clip(q_cand,j, q_j,min+δ_j, q_j,max−δ_j)`. Margin must be range-relative
  (or calibrated), not one shared radian value across joints — ranges differ per joint.
- Planned file: `srpdik/sr_ppo_dls/residual_action.py` (projection step) or a dedicated function
  therein; reuses `kinematics/joint_limit_utils.py::clip_to_operational_limits` semantics but
  with the SR-PPO-DLS-specific safety-margin table (not a straight reuse — locked
  `joint_limit_utils.py` must not be modified, per CLAUDE.md).
- Status: **REQUIRED**.

## 6. Safety filter (two-layer)

- PDF: §6.7 "Safety filter hai tầng", p.8 (eq. 40-44), plus §5.2-5.3 (p.6) for the Dalal et al.
  safety-layer framing this adapts.
  - **Layer 1 (hard feasibility)**: reject if NaN/Inf, non-finite FK/Jacobian, min joint-limit
    margin below a hard floor, or projection distance excessively large (frequent
    boundary-slamming).
  - **Layer 2 (one-step probe gate)**: run one DLS micro-update from both `q_initial` (→ q_B+)
    and `q_proj` (→ q_P+); accept `q_proj` only if normalized weighted error
    `E(q_P+) ≤ E(q_B+) + ε` and margin doesn't worsen past a threshold; otherwise fall back to
    `q_initial`. `ε ≥ 0` and the margin threshold are dev-tuned, then locked before validation
    (p.8, "phải được tune trên development và khóa trước validation").
  - Runtime cost of PPO inference, two-seed probe, and full DLS must be reported separately
    (p.8, "Chi phí của safety probe").
- Planned file: `srpdik/sr_ppo_dls/safety_filter.py`; reuses `kinematics/dls_solver.py::
  dls_single_update` for the probe, `kinematics/joint_limit_utils.py` for margins,
  `kinematics/pose_error.py` for weighted error `E(q)`.
- Status: **REQUIRED**. Directly testable: "safety fallback luôn trả seed hợp lệ" (p.17).

## 7. Locked DLS (unchanged solver)

- PDF: throughout, esp. §3.4 (p.3-4) and §9.3 (p.12-13, "no-retune" enforcement) and §12 (p.16,
  "Không sửa các module DLS/kinematics đã khóa"). SR-PPO-DLS never modifies
  `kinematics/dls_solver.py`, `kinematics/adaptive_damping.py`, or the candidate config
  `cand_D_pure_dls` (300 iters, adaptive damping, max joint step 0.1 rad, operational-limit
  clip). SR-PPO-DLS only changes the seed passed in.
- Existing repo asset that already satisfies this: `kinematics/dls_solver.py::
  solve_dls_until_converged`, `evaluation_v2/candidate_configs.py::candidate_by_id("cand_D_pure_dls")`.
  Confirm identical DLS config hash before/after SR-PPO-DLS runs (p.16, required test
  `test_sr_ppo_dls_lock_integrity.py`).
- Planned file: `srpdik/sr_ppo_dls/fingerprints.py` (config-hash check reusing
  `evaluation_v2/fingerprints.py::config_fingerprint` pattern, without modifying that module).
- Status: **REQUIRED** — this is a hard constraint, not a feature to build.

## 8. Paired pure-DLS baseline

- PDF: §7.1 (p.9, eq. 45-46), §9.4 (p.13, eq. 55-56). Every task must be evaluated twice with
  identical target/config/tolerance/max-iterations: `B = DLS(q_initial, T_d)` (baseline) and
  `H = DLS(q_seed, T_d)` (hybrid, seed possibly modified by SR-PPO-DLS). Reward and all reported
  metrics compare `H` against `B` on the *same* sample — never an absolute/unpaired score.
- Planned files: `srpdik/sr_ppo_dls/baseline_cache.py` (precompute/cache `B` once per task, must
  match a direct DLS rerun — required test, p.16), `srpdik/pipelines/cache_pure_dls_pointik.py`.
- Status: **REQUIRED**.

## 9. Reward

- PDF: §7 (p.9-10, eq. 47-53). Success indicators `S_k` at coarse/standard/strict tiers (eq. 47,
  reuses `evaluation_v2/candidate_configs.py::REPORTING_THRESHOLDS`, standard = primary metric).
  Reward = rescue bonus `c_R(1-S_B)S_H` − degradation penalty `c_D S_B(1-S_H)` (with `c_D > c_R`)
  + error-improvement term `c_E·clip(E_B−E_H,-1,1)` + iteration-improvement term (only when both
  succeed) `c_I·clip((I_B−I_H)/I_max,-1,1)` − action-norm penalty `c_a‖a‖²` − joint-limit-margin
  penalty `c_m·m(q_seed)` − near-singularity penalty `c_σ·σ(q_seed)` − fallback penalty
  `c_F·I[fallback]`. Limit/singularity penalty functions given explicitly (eq. 52-53).
- §7.4 (p.10): reward weights `{c_R,c_D,c_E,c_I,c_a,c_m,c_σ,c_F,ε,δ}` are hyperparameters to be
  searched (TPE, §8.5), never hardcoded as a "theoretical conclusion".
- Planned file: `srpdik/sr_ppo_dls/paired_reward.py`. Required test: "paired reward: rescue
  positive, degradation negative" (p.16).
- Status: **REQUIRED** (formula + attribution terms); reward *weight values* are
  **OPTIONAL**/tunable, not fixed by the PDF.

## 10. Curriculum

- PDF: §8.2 "Sampling theo failure mode", p.10 (5-stage table, stages 0-4): (0) near-target/easy
  → learn `a≈0`/reduce degradation; (1) fast-success cases → preserve success, cut
  iterations/runtime; (2) stagnation/far-target/large-orientation/hard-initial → learn basin
  rescue; (3) balanced across 6 difficulty groups → generalize over full Point-IK distribution;
  (4) trajectory waypoint-0 development set → measure effect on the whole warm-start chain.
  Stage progression uses stage-local budget + gate, with rollback if degradation rises
  (p.10, "Có rollback nếu stage mới làm degradation tăng").
- Planned file: `srpdik/pipelines/train_sr_ppo_dls.py` (curriculum scheduler),
  `srpdik/sr_ppo_dls/` config for per-stage sampling weights.
- Status: **REQUIRED** at the design level; exact stage budgets/gates are **OPTIONAL**
  (dev-tuned).

## 11. Dataset policy

- PDF: §8.1 (p.10) and §9.1/9.3 (p.12, Figure 2). SR-PPO-DLS must NOT train on
  development/validation/frozen_test directly as its only data source — it needs an
  **independent online training stream** using the same target-generation logic but a distinct
  seed namespace, with a content-hash check confirming zero overlap with the three fixed splits.
  Fixed dataset v2 splits keep their existing roles: development → TPE/reward tuning/curriculum/
  ablation/checkpoint selection; validation → single confirmation run of a locked config, no
  retuning; frozen_test → single final paired evaluation after code/config/model fingerprint
  lock, reusing the existing frozen pure-DLS artifact as the fixed baseline. Training the stream
  must not modify Dataset v2.0.0 itself.
- Planned files: `srpdik/pipelines/build_sr_ppo_training_stream.py`; reuses
  `dataset_v2/seeds.py::derive_seed`/`rng_from` with a new tag (do not touch `dataset_v2/seeds.py`
  itself — call it with a new namespace tag), `dataset_v2/point_ik_generation.py`'s generation
  logic as read-only reference.
- Status: **REQUIRED**.

## 12. Leakage policy

- PDF: §6.3 field-exclusion list (p.7, above), §9.2 (p.12-13, field-mapping table): environment
  may only see `q_initial`, `target_position`, `target_quaternion_wxyz`,
  `difficulty_id`/`name` (report/ablation only, never policy input), `sample_id` (paired join
  key). **Never** `q_target_reference` or any protected field. §14.3 (p.18) also flags
  memorization risk from looping 1,200 dev tasks — mitigated by the independent training stream
  (item 11) + content-hash anti-leakage + randomized target generation.
- Existing repo asset: `evaluation_v2/protected_guard.py::assert_no_protected_fields` /
  `PROTECTED_FIELD_NAMES` already enforces this pattern for v2 evaluation; SR-PPO-DLS's
  environment/observation code must call an equivalent guard (new function in
  `srpdik/sr_ppo_dls/observation.py` or reuse `evaluation_v2.protected_guard` directly — decide
  in Phase C, see `SRPDIK_IMPLEMENTATION_PLAN.md`).
- Status: **REQUIRED**. Required test: `test_sr_ppo_no_protected_fields.py` (p.16).

## 13. Evaluation

- PDF: §10 (p.13-15). Mandatory baselines (§10.1, p.13-14): pure DLS; random-residual+DLS;
  DLS-probe-heuristic-seed+DLS (no learning); PPO-residual-without-safety-filter+DLS (safety
  ablation); PPO-residual-without-DLS-probe-feature+DLS (observation ablation); SR-PPO-DLS full.
  Point-IK metrics (§10.2, p.14): per-split/per-difficulty-group coarse/standard/strict success,
  rescue/degradation counts, net success gain, position/orientation median/P95/max, DLS
  iterations median/P95, failure-reason counts (esp. stagnation), PPO action norm/clip rate,
  safety fallback rate, min joint-limit margin/σ_min, runtime P50/P95/P99 split by
  PPO/filter/DLS/total, non-finite count. Trajectory metrics (§10.3, p.14) for the waypoint-0
  application: waypoint standard success, position/orientation RMSE/P95/max, first-failure
  location, max failure streak, recovery rate, cross-track RMSE/P95, final progress
  ratio/coverage, path-length ratio, max joint jump, total joint variation, velocity/jerk,
  total runtime. Paired statistics (§10.4, p.15): paired bootstrap 95% CI on success difference
  `d_i = S_H,i - S_B,i`, McNemar test on rescue-vs-degradation discordant pairs (eq. 60).
  Acceptance gates (§10.5, p.15, 7 gates) must be pre-registered on development before
  validation: standard-success CI excludes 0; degradation rate under a locked threshold; rescue
  count > degradation count with clear margin; no non-finite increase; runtime P99/fallback rate
  within locked budget; improvement not from one difficulty group only; trajectory waypoint-0
  experiment doesn't materially worsen joint jump/smoothness.
- Planned files: `srpdik/evaluation_v2/sr_ppo_point_eval.py`,
  `srpdik/evaluation_v2/sr_ppo_trajectory_init_eval.py`; reuses
  `evaluation_v2/point_eval.py`/`trajectory_eval.py` result shapes and
  `evaluation_v2/candidate_configs.py::REPORTING_THRESHOLDS` as read-only references (do not
  edit those locked modules).
- Status: **REQUIRED** (metrics, baselines, gates); exact gate thresholds are **OPTIONAL**
  (dev-locked, not stated numerically in the PDF beyond "gates must be pre-registered").

## 14. Kaggle training

- PDF: **NOT FOUND**. The text was grepped for "Kaggle", "GPU", "colab" — zero matches. The PDF's
  training-loop section (§8.3-8.4, p.10-11) only notes "DLS chủ yếu CPU" (DLS is mostly CPU-bound)
  as a config-table remark; it does not prescribe Kaggle or any specific compute platform.
- Repo context (not PDF-derived): the project already has a Kaggle release pattern for Dataset
  v2 (`scripts/package_kaggle_release.py`, `notebooks/KR810_Tier0_Tier4_Kaggle_Template.ipynb`,
  `tests/test_kaggle_notebook.py`, `tests/test_kaggle_release_package.py`). If Kaggle is later
  chosen as the SR-PPO-DLS training environment, mirror that pattern under
  `srpdik/notebooks/`/`srpdik/scripts/` — but this is a project decision, not a PDF requirement.
- Status: **OPTIONAL** — infra choice deferred; no PDF mandate to reconcile.

## 15. Inherited vs. new-proposal content (PDF §11, p.15-16 traceability table)

| Component | Inherited from | Adapted how |
|---|---|---|
| PPO-Clip objective | Schulman et al. [2] | Standard clipped surrogate for continuous 7-D residual action, multi-epoch minibatch, actor-critic. |
| "PPO improves seed, DLS refines pose" idea | Yu & Tan [1] | Kept the core hypothesis; project uses one-shot seed correction, not their alternating multistep scheme. |
| Residual decomposition | Johannink et al. [3] | Base solver (DLS) kept strong; residual moved from controller-output space to joint-space seed. |
| Safety layer / action projection | Dalal et al. [4] | Adapted to IK: hard joint-range projection + DLS-probe accept/fallback gate, not their closed-form linear-constraint safety layer. |
| TPE hyperparameter search | Shianifar et al. [5] | Applied to action scale, LR, entropy, clip range, network width, safety tolerance — tuned on development only. |
| DLS damping near singularity | Buss & Kim [6] | Explanatory only — locked solver's damping is unchanged; PPO does not touch this. |
| Dataset split / anti-leakage / frozen protocol | Project's own `CHATGPT_DLS_CURRENT_STATE_BRIEF.md` [7], `V2_IMPLEMENTATION_LOG.md` [8] | Extended with an SR-PPO-DLS-specific independent training stream + method-level no-retune enforcement. |

- PDF explicitly states (p.16, "Tuyên bố nguồn gốc"): no single paper describes the full
  SR-PPO-DLS design — it is a project-original synthesis with per-component traceability, not a
  reproduction of any one paper.

## 16. Explicit non-implementation items (this phase and beyond, unless re-scoped)

| Item | PDF citation | Status |
|---|---|---|
| Multistep PPO (PPO re-invoked at every DLS iteration/waypoint) | §1 p.1 ("Không phát triển Multistep PPO"), §9.6 p.13 ("Tại sao không PPO ở mỗi waypoint" — explicit user decision) | **OUT_OF_SCOPE** |
| MAPPO / multi-agent PPO | Not mentioned in PDF; excluded per CLAUDE.md scope and this prompt's explicit exclusion list | **OUT_OF_SCOPE** |
| Dynamics, actuator, controller, torque, collision, payload, compliance, backlash, sensor noise, TCP calibration | §2.2 p.2 ("Không xét torque, actuator, controller, collision, payload, compliance, backlash, sensor noise hoặc TCP đã hiệu chuẩn"); mirrors CLAUDE.md's global scope exclusion | **OUT_OF_SCOPE** |
| Real-robot / ISO certification claims | §2.2 p.2 ("success là success của numerical IK trong MuJoCo model, không phải chứng nhận độ chính xác robot vật lý"); §14.6 p.18 | **OUT_OF_SCOPE** |
| Modifying locked DLS/kinematics modules | §12 p.16 | **OUT_OF_SCOPE** (hard constraint, see item 7) |
| Algorithm/training implementation itself | This prompt's explicit instruction ("Không triển khai thuật toán hoặc training trong prompt này") | **OUT_OF_SCOPE for this phase only** — planned for later phases per `SRPDIK_IMPLEMENTATION_PLAN.md`. |

## 17. Risks flagged by the PDF (§14, p.17-18) — carry into implementation plan risk register

- §14.1 (p.17-18): one-step PPO is close to a contextual bandit; critic may add little value —
  plan an ablation vs. REINFORCE/bandit baseline and a supervised ranking baseline.
- §14.2 (p.18): reward hacking via fallback (policy proposes garbage, relies on filter rejecting
  it to avoid penalty) — mitigate with fallback-rate logging, small fallback penalty, checkpoint
  gating on fallback rate.
- §14.3 (p.18): memorization from looping 1,200 dev tasks — mitigated by independent training
  stream (item 11).
- §14.4 (p.18): action scale `α` too small ⇒ no basin change; too large ⇒ branch-switching and
  projection clipping — must be TPE-tuned against a rescue-minus-degradation objective.
- §14.5 (p.18): safety filter too conservative ⇒ SR-PPO-DLS degenerates to pure DLS; too loose ⇒
  loses do-no-harm guarantee — report acceptance/fallback rate and improvement conditional on
  accepted proposals.
- §14.6 (p.18): no claim of generalization to the physical robot.
