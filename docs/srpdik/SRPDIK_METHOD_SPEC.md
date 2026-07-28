# SR-PPO-DLS — Method Spec Traceability (Phase 1)

Traces each PDF-derived requirement to the config/source that locks its structure and the test
that verifies it. Only Phase 1 rows are listed here (locked pure-DLS snapshot, structural
config lock, split guard, audit CLI). No behavior beyond that is implemented yet: rows are
marked **CONFIGURED** (structure/policy locked in a config/module, ready to be consumed) or
**PLANNED** (structure locked, but numeric values/behavior are deferred to a later phase) --
never "implemented" for anything past Phase 1. See `docs/srpdik/SRPDIK_IMPLEMENTATION_PLAN.md`
for the full phase table and `docs/srpdik/DECISIONS.md` #10 for why this session uses
"Phase 1/1A/..." naming.

| PDF requirement | Config/source | Test | Status |
|---|---|---|---|
| Locked pure-DLS candidate (`cand_D_pure_dls`), never retuned (PDF §3.4, §9.3, §12) | `configs/srpdik/dls_locked.json`; `srpdik/dls_lock.py` (`load_dls_lock`, `verify_candidate_name`, `verify_source_hashes`, `verify_resolved_parameters_match_live_source`, `verify_dls_lock`, `get_locked_candidate_config`); source of truth: `evaluation_v2/candidate_configs.py::candidate_by_id("cand_D_pure_dls")` | `tests/srpdik/test_dls_lock.py` (candidate name, source-hash tamper detection, resolved-parameter drift detection, timestamp stability, byte-identical no-op verification); `tests/srpdik/test_srpdik_audit.py` (audit CLI pass/fail on the lock) | **CONFIGURED** |
| Observation, 36-D, fixed field order + forbidden-field exclusion list (PDF §6.3, eq. 33) | `configs/srpdik/srpdik_observation.json` (`observation_dim`, `fields`, `forbidden_fields`) | `tests/srpdik/test_configs.py::test_observation_dims_sum_to_36`, `test_config_passes_path_and_leakage_policy`, `test_allows_protected_field_name_as_documentation_value` | **CONFIGURED** (dims/field order locked); observation *computation* itself is **PLANNED** (`srpdik/features/` is an empty scaffold) |
| Residual action, 7-D, do-no-harm invariant + seed projection (PDF §6.5-6.6, eq. 35-39) | `configs/srpdik/srpdik_action.json` (`action_dim`, `residual_formula`, `do_no_harm_invariant`, `projection`) | `tests/srpdik/test_configs.py::test_action_dim_matches_constant`, `test_config_passes_path_and_leakage_policy` | **CONFIGURED** (formula/invariant locked; margin values, action-scale numerics deferred); action *computation* is **PLANNED** (`srpdik/policy/` is an empty scaffold) |
| One-shot SR-PPO-DLS scope: no Multistep PPO, no MAPPO, no dynamics/actuator/controller/torque/collision, no real-robot/ISO claims (PDF §1, §2.2, §9.6) | `configs/srpdik/srpdik_method.json` (`scope.one_shot_ppo_residual: true`, `scope.multistep_ppo: false`, `scope.mappo: false`, `scope.dynamics_actuator_controller_torque_collision: false`, `scope.real_robot_or_iso_certification_claims: false`) | `tests/srpdik/test_configs.py::test_required_metadata_fields_present`, `test_config_passes_path_and_leakage_policy` (parses/loads cleanly with these flags set) | **CONFIGURED** |
| Protected-data / leakage prohibition: never `q_reference`/`q_target_reference`/`q_source_reference`/`waypoint_reachable`/reconstruction-error fields as live policy input (PDF §6.3, §9.2, §12) | `configs/srpdik/srpdik_data.json` (`leakage_policy.forbidden_fields`, `leakage_policy.allowed_environment_fields`); `srpdik/config.py::assert_config_policy` (rejects a forbidden substring as a live config *key*); `srpdik/constants.py::FORBIDDEN_FIELD_SUBSTRINGS` | `tests/srpdik/test_configs.py::test_rejects_protected_field_as_live_key`, `test_allows_protected_field_name_as_documentation_value` | **CONFIGURED** (policy + guard exist); a dedicated runtime observation-side guard (mirroring `evaluation_v2.protected_guard.assert_no_protected_fields`) is **PLANNED** for the Phase implementing `srpdik/features/observation.py` |
| Frozen-test prohibition: `frozen_test` never accessed by the current pipeline; `validation` requires explicit authorization (PDF §8.1, §9.1-9.3) | `configs/srpdik/srpdik_data.json` (`splits.frozen_test.access: "denied"`, `splits.validation.access: "requires_explicit_authorization"`); `srpdik/data/split_guard.py::assert_split_access_allowed` / `is_split_access_allowed` | `tests/srpdik/test_split_guard.py` (frozen_test denied even with `validation_authorized=True`; validation denied without authorization, allowed with it; frozen-marker path rejected regardless of declared split; unknown/ambiguous split names rejected) | **CONFIGURED** |
| PDF reference integrity (byte-identical source, Phase 0 SHA256) | `srpdik/constants.py::PDF_REFERENCE_RELATIVE_PATH` / `PDF_REFERENCE_SHA256` | `tests/srpdik/test_reference_hash.py` (hash match + single-byte tamper detection) | **CONFIGURED** |
| Repo-relative, CWD-independent path resolution (mirrors `utils/dataset_locator.py`, no frozen-test default) | `srpdik/paths.py` | `tests/srpdik/test_paths.py` (CWD-independence, no absolute-path literals in code, no default split reference in code, package import smoke test) | **CONFIGURED** |
| Read-only Phase 1 audit surface (metadata/source integrity, no solver/generation/evaluation run) | `pipelines/run_srpdik_audit.py` | `tests/srpdik/test_srpdik_audit.py` (pass on the real repo; usage-error exit 2 on a bad `--dataset-v2-root`; exit 1 on simulated lock/config/candidate/frozen-guard failures; pass/fail against a real Dataset v2 scaffold) | **CONFIGURED** |

## Deferred to later phases (not rows above because no Phase 1 config/test exists yet)

Safety filter numeric thresholds, reward weight values, curriculum stage budgets/gates,
TPE hyperparameter search space, and the full evaluation acceptance-gate thresholds are all
locked at the *structural* level in atomic task 2's configs (`srpdik_safety.json`,
`srpdik_reward.json`, `srpdik_curriculum.json`, `srpdik_training.json`,
`srpdik_evaluation.json`, each marked `"implementation_status"` inside the file itself) but
carry no traceability row here because the PDF requirements doc
(`docs/srpdik/SRPDIK_REFERENCE_REQUIREMENTS.md`) marks their concrete values **OPTIONAL**
(dev-tuned), not a Phase 1 deliverable.
