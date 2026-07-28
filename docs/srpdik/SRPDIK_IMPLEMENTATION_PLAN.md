# SR-PPO-DLS — Implementation Plan

Phases below follow PDF §13 (p.17, "Quy trình triển khai theo giai đoạn") with package names
substituted per `DECISIONS.md` #1-2. Each phase's gate is the PDF's own gate (translated) unless
noted. No phase after Phase 0 is started yet.

| Phase | Work | Gate (must pass before moving on) |
|---|---|---|
| **0** (this phase) | PDF ingestion, source audit, source map, handoff docs. No code. | All Phase 0 output files exist; baseline `pytest -q` result recorded (pass/fail counts, not necessarily 100% green). |
| **A** | Aggregate existing DLS failure modes by difficulty/init class from the locked frozen Point-IK + trajectory results (`docs/CHATGPT_DLS_CURRENT_STATE_BRIEF.md`, `final_dls_summary.json`). Produce a stagnation/iteration/success/margin/σ_min table. | Table produced from real frozen numbers, reconciling the 95.08%/0.951 discrepancy (`DECISIONS.md` #9). |
| **B** | Build the independent SR-PPO-DLS training stream generator (`srpdik/pipelines/build_sr_ppo_training_stream.py`), reusing `dataset_v2/point_ik_generation.py` logic read-only with a new `derive_seed` tag namespace. | Anti-leakage pass (content-hash disjoint from dev/val/frozen); all generated targets reachable; no protected fields present. |
| **C** | Baseline cache: precompute pure-DLS result `B` for every training-stream + dev/val/frozen task via `srpdik/sr_ppo_dls/baseline_cache.py` + `srpdik/pipelines/cache_pure_dls_pointik.py`. | Recompute audit: cached `B` matches a direct `solve_dls_until_converged` rerun; config hash locked and recorded. |
| **D** | Environment + observation/action/safety-filter modules: `srpdik/sr_ppo_dls/{observation,residual_action,safety_filter}.py`, `srpdik/envs/kr810_sr_ppo_dls_env.py`. | Unit tests (`test_sr_ppo_observation.py`, `test_sr_ppo_safety_filter.py`, `test_sr_ppo_no_protected_fields.py`) pass; a random policy produces zero non-finite results. |
| **E** | Reward module (`srpdik/sr_ppo_dls/paired_reward.py`) + PPO actor-critic + training loop (`srpdik/pipelines/train_sr_ppo_dls.py`), Stage-0 do-no-harm training only. | Degradation low; action near zero on easy/near-target tasks. |
| **F** | Curriculum stages 1-4 (high-iteration/stagnation/far-target/hard-initial/balanced/waypoint-0-dev), stage-local budgets + rollback-on-degradation. | Rescue count increases on development without degradation regression. |
| **G** | TPE hyperparameter search + multi-seed selection (5 seeds per PDF §8.4) over the space in PDF §8.5 (p.11-12), development/training-stream only. | Stable config selected across seeds, not cherry-picked from one seed. |
| **H** | Validation confirmation: run the exact locked config once on the `validation` split, no retuning after. | Single run, no post-hoc config changes. |
| **I** | Trajectory waypoint-0 secondary application (`srpdik/evaluation_v2/sr_ppo_trajectory_init_eval.py`) — SR-PPO-DLS only at waypoint 0, warm-start DLS for waypoints 1-399. | Measured effect on full 400-waypoint warm-start chain vs. baseline warm-start; no PPO re-invocation mid-trajectory (`DECISIONS.md` #7). |
| **J** | Frozen final: fingerprint lock (code+config+model), open SR-PPO-DLS's own frozen-ledger entry (distinct from the pure-DLS run's), single paired evaluation against the mandatory baselines (PDF §10.1), full metrics + paired statistics + acceptance gates (PDF §10.2-10.5). | All 7 acceptance gates (PDF §10.5, p.15) checked; no-retune statement recorded; frozen_test accessed exactly once for this method. |

## Required tests (PDF §12.1, p.17) to add across phases D-J

`test_sr_ppo_observation.py`, `test_sr_ppo_safety_filter.py`, `test_sr_ppo_no_protected_fields.py`,
`test_sr_ppo_paired_reward.py`, `test_sr_ppo_dls_lock_integrity.py` — see
`docs/srpdik/SRPDIK_REFERENCE_REQUIREMENTS.md` items 3, 6, 7, 8, 9, 12 for what each must assert.

## Explicitly not planned (any phase)

Multistep PPO, MAPPO, dynamics/actuator/controller/torque/collision work, real-robot claims —
see `DECISIONS.md` #7.

## Next atomic task after Phase 0

Phase A, step 1: read `final_dls_summary.json` from the frozen public export root (find the
exact path via `evaluation_v2` release artifacts referenced in
`docs/CHATGPT_DLS_CURRENT_STATE_BRIEF.md`) and reconcile the success-rate figures per
`DECISIONS.md` #9. This is read-only (no dataset v1/v2 mutation, no frozen_test *generation*
access — reading an already-released summary file is not a new frozen-test access event).
