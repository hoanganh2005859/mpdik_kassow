# SR-PPO-DLS — Implementation Log (append-only)

Format per entry: date, phase, action, files touched, test run (if any), decision made (if any).
Do not paste long source excerpts here — point to the file/commit instead.

---

## 2026-07-28 — Phase 0

- Start state: branch `feature/dataset-v2`, dirty tree (`SR_PPO_DLS_KR810_Theory_and_Dataset_Application.pdf`
  and `docs/srpdik/DLS_TRAJECTORY_PLOT_DIAGNOSIS.md` untracked, pre-existing). Per protocol, no
  branch created, no commit performed this phase (`DECISIONS.md` #4).
- Located PDF at repo root; copied to `docs/srpdik/references/...pdf`; SHA256
  `b9a9fe0c65719ccbcfb7cf92bbea4b72b016d6a1c43f91892614bdfad0c96395`.
- Extracted full text via `pdftotext -layout` (text layer present, no OCR needed); saved to both
  `srpdik/docs/srpdik/references/...txt` (literal prompt path) and
  `docs/srpdik/references/...txt` (mandatory Phase-0 output path) — see `DECISIONS.md` #3.
- Read the full 1262-line extracted text (all 20 pages, not just the first few).
- Delegated a read-only source audit (19-point checklist covering kinematics/, algorithms/,
  dataset_v2/, evaluation_v2/, configs/, tests/, docs) to an Explore subagent to keep this
  session's context light; findings folded into `SRPDIK_SOURCE_MAP.md` and
  `SRPDIK_REFERENCE_REQUIREMENTS.md`.
- Wrote `SRPDIK_REFERENCE_REQUIREMENTS.md` (17 sections mapping PDF content to
  REQUIRED/OPTIONAL/OUT_OF_SCOPE implementation items, with page citations).
- Wrote `SRPDIK_SOURCE_MAP.md` (57 lines, within the 300-line cap).
- Wrote `DECISIONS.md` (9 locked decisions), `ARTIFACT_INDEX.md`,
  `SRPDIK_IMPLEMENTATION_PLAN.md` (phases 0-J mirroring PDF §13).
- Ran baseline `pytest -q` (full suite, no dataset generation/evaluation/training triggered):
  **793 passed, 0 failed, 3308.11s**. Result recorded in `PHASE_STATUS.json` / `HANDOFF.md`.
- No dataset v1 or v2 files modified. No frozen_test split accessed. No training run.
- Phase 0 marked complete in `PHASE_STATUS.json`. Handoff ready for Phase A (see
  `NEXT_COMMANDS.md` PROMPT 1).

## 2026-07-28 — Phase 1 (session start)

- Fresh session after `/clear`. Read state files in required order; confirmed Phase 0 `complete`,
  PDF SHA256 match, `cand_D_pure_dls` referenced consistently.
- Found a real conflict: the locked `SRPDIK_IMPLEMENTATION_PLAN.md`/`HANDOFF.md`/`PHASE_STATUS.json`
  /`NEXT_COMMANDS.md` all queued **Phase A** (read-only frozen success-rate reconciliation) as the
  next atomic task; this session's governing prompt instead defines a new **"Phase 1 — Scaffold +
  locked pure-DLS snapshot"** that writes code/config (scaffold, DLS lock, split guard, audit CLI)
  and defers Phase-A-style analysis to "Phase 1A" afterward — reversing the locked plan's
  analysis-before-code order. Presented this conflict to the user (did not guess); user chose
  "proceed with new Phase 1." Recorded as `DECISIONS.md` #10 (phase renumbering, "Phase
  1/1A/..." supersedes "0/A/B/C/..." going forward; no math/algorithm decision changed).
- `git status --short`: only `?? docs/srpdik/` (untracked) — working tree dirty by this session's
  own definition. Per its git-safety rule: no branch created, no commit at end regardless of gate
  completion; `commit_status = "skipped_dirty_tree"` recorded in `HANDOFF.md`.

### Atomic task 1 — scaffold + paths.py

- Created `srpdik/` subpackages (`data`, `features`, `policy`, `envs`, `training`, `evaluation`,
  `kaggle`) plus top-level `constants.py`, `exceptions.py`, `paths.py`, `config.py`,
  `manifests.py`, `dls_lock.py` (placeholder, filled in atomic task 3), and
  `srpdik/data/split_guard.py` (placeholder, filled in atomic task 4).
- Created `configs/srpdik/`, `tests/srpdik/`, `notebooks/srpdik/`, `results/srpdik/` (empty dirs
  get a `.gitkeep`).
- `paths.py` derives `REPO_ROOT` from `Path(__file__).resolve().parent.parent` (mirrors
  `utils/dataset_locator.py`); no hardcoded absolute path; no disk scanning; no default frozen-test
  path. Verified CWD-independence by running the import from `docs/` with an explicit
  `PYTHONPATH` — `repo_root()` still resolved to the true repo root.
- Reviewed source for the upcoming DLS lock while here: `evaluation_v2/candidate_configs.py`
  (`cand_D_pure_dls` = 300 iters, adaptive damping, `lambda_max=0.2`, `lambda_min=1e-4`,
  `max_joint_step_rad=0.1`, `clip_to_operational_limits=True`, `joint_limit_avoidance=False`,
  `null_space_gain=0.0`, `singularity_sigma_threshold=0.03`, `position_weight=1.0`,
  `orientation_weight=0.2`; convergence tolerance fixed at strict tier 1mm/1deg for every
  candidate; coarse/standard/strict = 6mm/5deg, 3mm/2deg, 1mm/1deg); `kinematics/dls_solver.py`
  (stagnation window 5, min relative improvement 1e-3, both hardcoded module constants, not
  candidate-config fields); `kinematics/pose_error.py` (world-frame convention:
  `orientation_error = Log(R_target @ R_current.T)^vee`, position `target - current`);
  `kinematics/jacobian.py` (world/space-frame geometric Jacobian via `mj_jacSite`);
  `configs/robot_config.json` (`end_effector_site = "ee_site"`, 7 revolute joints); confirmed
  `cand_D_pure_dls`'s `solver_config()` is passed as an explicit dict, so
  `configs/dls_config.json` (the v1 default) is NOT part of this candidate's actual runtime
  config path and will not be included in the lock's hashed file set.
- Import smoke test: all `srpdik.*` submodules import cleanly; `srpdik.paths.repo_root()`
  correct from a non-repo-root CWD. No `pytest` run yet for this atomic task (no tests exist
  for it beyond the smoke import).
- No dataset v1/v2 file touched. No frozen_test accessed. No generation/evaluation/training run.

### Atomic task 2 — configs/srpdik/*.json

- Created 9 method configs: `srpdik_method.json`, `srpdik_observation.json`,
  `srpdik_action.json`, `srpdik_safety.json`, `srpdik_reward.json`, `srpdik_training.json`,
  `srpdik_curriculum.json`, `srpdik_evaluation.json`, `srpdik_data.json`. Each has
  `schema_version`/`method_version`/`description`, sorted (deterministic) keys, no absolute
  path, no timestamp. `dls_locked.json` deliberately deferred to atomic task 3.
- Observation config locks the 36-D composition (7+3+3+7+7+1+1+7 = 36) and a `forbidden_fields`
  documentation list; action config locks the 7-D residual + projection formulas and the
  do-no-harm invariant; safety/reward/training/curriculum/evaluation configs lock PDF-derived
  structure while explicitly marking untuned numeric values (margins, epsilon, TPE
  hyperparameters, gate thresholds) as "dev-tuned in a later phase, not fixed here" per
  `SRPDIK_REFERENCE_REQUIREMENTS.md`'s REQUIRED-structure-vs-OPTIONAL-values split; data config
  locks the split-access policy consumed by `srpdik/data/split_guard.py` (atomic task 4).
- Fixed a real design gap in `srpdik/config.py`'s policy check: the observation/data configs
  must legitimately *document* the forbidden-field names (required by items 3/12 of the
  requirements doc, and consistent with `evaluation_v2/protected_guard.py`'s own
  `PROTECTED_FIELD_NAMES` pattern) but must never let one become a live, wired-in config *key*.
  Reworked `assert_config_policy` to check dict keys (not arbitrary string values) for
  protected-field substrings, and string values (not keys) for absolute paths, so a
  `"forbidden_fields": ["q_target_reference"]` documentation entry passes while a live key like
  `"q_target_reference_source": "..."` would still fail closed.
- Verified: all 9 configs load and pass metadata/policy checks via
  `srpdik.manifests.build_srpdik_config_manifest()`.
- No dataset v1/v2 file touched. No frozen_test accessed. No generation/evaluation/training run.

### Atomic task 3 — lock cand_D_pure_dls

- Confirmed `cand_D_pure_dls` from `evaluation_v2/candidate_configs.py::candidate_set()` (5th
  candidate: 300 iters, adaptive damping, `lambda_max=0.2`/`lambda_min=1e-4`,
  `max_joint_step_rad=0.1`, `clip_to_operational_limits=True`, `joint_limit_avoidance=False`,
  `null_space_gain=0.0` -- isolates the pure DLS term by disabling null-space centering that the
  other 4 candidates use).
  - Traced the solver call graph from `kinematics/dls_solver.py` and hashed its full transitive
    numeric dependency closure, not just the 7 files named as the floor in the prompt: added
    `kinematics/forward_kinematics.py`, `kinematics/model_loader.py`,
    `kinematics/rotation_utils.py` (all directly imported by `dls_solver.py` and load-bearing
    for every solve), plus `configs/robot_config.json` + `assets/kr810.xml` (the model/robot
  config actually used to build the `ModelContext`). Excluded `kinematics/quaternion_utils.py`
  (only feeds an unused `FKResult.quaternion_wxyz` field, not consumed by pose error/DLS math)
  and `utils/config_loader.py` (only used for `load_dls_config()`'s default path; the locked
  candidate always passes an explicit `solver_config()` dict, so this file is not in the actual
  runtime call path for `cand_D_pure_dls`).
- Wrote `configs/srpdik/dls_locked.json` (29 top-level fields, sorted keys) with:
  `candidate_name`, `immutable: true`, `source_config_relative_path`/`source_config_sha256`,
  12-file `source_code_files` SHA256 map, `resolved_parameters` (verbatim
  `candidate_by_id("cand_D_pure_dls").solver_config()` output), pose-error/Jacobian
  frame+convention notes, `end_effector_site: "ee_site"`, damping/lambda/singularity/iteration/
  step/clip/joint-limit/stagnation/min-relative-improvement fields, coarse/standard/strict
  thresholds, `snapshot_git_commit` (`0c6dcf0768f2ff4f142ccf572a4518684846b183`),
  `snapshot_timestamp_utc` (`2026-07-28T09:06:28+00:00`, generated once), `lock_format_version`.
  All source paths are repo-relative; no sibling Dataset v2 root referenced.
- Wrote `srpdik/dls_lock.py`: `load_dls_lock()` (schema/required-field check),
  `verify_candidate_name()`, `verify_source_hashes()` (recomputes SHA256 for all 12 files,
  reports every mismatch, not just the first), `verify_resolved_parameters_match_live_source()`
  (extra cross-check: re-reads `candidate_by_id(...).solver_config()` live and diffs it against
  the lock's `resolved_parameters`, independent of the hash check -- catches a lock-file
  transcription bug even if source hashes still match), `verify_dls_lock()` (runs all of the
  above), `get_locked_candidate_config()`. All fail-closed via `DLSLockVerificationError`.
- Verified end-to-end: `verify_dls_lock()` passes against the live repo. Tamper test: flipped
  one hash in `dls_locked.json` (`kinematics/dls_solver.py` -> all-zeros), confirmed
  `verify_dls_lock()` raises `DLSLockVerificationError` naming exactly that file, then restored
  the original file and re-verified clean. No source/config DLS file was modified by this
  process (tamper test only edited a scratch copy comparison target file transiently and
  restored it).
- No dataset v1/v2 file touched. No frozen_test accessed. No generation/evaluation/training run.

### Atomic task 4 — split guard

- Implemented `srpdik/data/split_guard.py`: `assert_split_access_allowed(split_name, *, path=,
  validation_authorized=)` -> canonical split name or raises `SplitAccessDenied`;
  `is_split_access_allowed(...)` non-raising wrapper. Policy: `train`/`development` allowed;
  `validation` requires `validation_authorized=True`; `frozen_test` always denied (no
  frozen-evaluation CLI in Phase 1). Fail-closed: unknown/ambiguous split names rejected via a
  strict, exact-match alias table (no fuzzy "test"/"frozen" aliases, to avoid accidentally
  mapping an unrelated word onto the frozen split); any path string containing a
  frozen-test marker (`frozen_test`, `frozen-test`, `eval_frozen`) is rejected regardless of the
  declared split name (defence in depth). Never opens or reads split contents -- name/path
  reasoning only.
- Verified: train/development allowed; validation denied without authorization, allowed with
  it; frozen_test denied even with `validation_authorized=True`; unknown split (`bogus_split`,
  bare `test`) denied; a development-labeled path containing an `eval_frozen` marker denied
  despite the split name.
- No dataset v1/v2 file touched. No frozen_test accessed (not even a path check needed to read
  its content). No generation/evaluation/training run.

### Atomic task 5 — audit CLI

- Wrote `pipelines/run_srpdik_audit.py` (mirrors the existing `pipelines/run_dataset_v2_*.py`
  argparse/exit-code style). Checks, in order: repo root + git state (commit, dirty-file
  count via `git status --short`, read-only); PDF reference existence + SHA256 (added
  `PDF_REFERENCE_RELATIVE_PATH`/`PDF_REFERENCE_SHA256` to `srpdik/constants.py`); all 9 srpdik
  configs parse (`srpdik.manifests.build_srpdik_config_manifest`); DLS lock parses; DLS lock
  source/config hashes + live resolved_parameters match; candidate name is `cand_D_pure_dls`;
  Dataset v1 immutability (recomputes SHA256 for every file in
  `benchmarks/point_ik/point_ik_checksum.json` + `benchmarks/validation/validation_checksum.json`
  `"files"` lists, plus every row's `sha256` column in `trajectories/trajectory_manifest.csv` --
  14 files total, all read-only, no v1 file modified); Dataset v2 public root (only if
  `--dataset-v2-root` is passed -- checks `DATASET_MANIFEST.json` + checksum-manifest file
  *existence* only via `dataset_v2.locator.require_dataset_v2_root`, no sibling-directory scan,
  no frozen_test content read); frozen_test denied by default
  (`srpdik.data.split_guard.is_split_access_allowed("frozen_test")` must be False); dependency
  availability (numpy/scipy/mujoco/pytest required -> fail if missing;
  gymnasium/stable_baselines3/torch optional -> warn only, never flips exit code).
- Exit codes: `--dataset-v2-root` pointing at a non-existent directory -> usage error, exit 2
  (verified). Any `fail`-status check -> exit 1 (verified via a temporary `candidate_name`
  tamper: correctly reported both the hash/resolved_parameters mismatch and the candidate-name
  mismatch, then the file was restored to `cand_D_pure_dls` and a clean re-run returned exit 0).
  All checks pass, no `--dataset-v2-root` -> exit 0 (verified).
- No dataset v1/v2 file modified (`git status --short` confirms no unexpected new/changed paths
  outside srpdik's own scaffold after the tamper-and-restore test). No frozen_test accessed. No
  solver/evaluation/generation run by the CLI itself.

### Tests (tests/srpdik/*) + traceability table

- Wrote all 6 required test files: `test_paths.py` (import smoke test, CWD-independence, no
  hardcoded absolute path / default split literal in code), `test_configs.py` (all 9 configs
  parse, required metadata, 36-D/7-D dim checks, absolute-path rejection, protected-key
  rejection, documentation-value exemption, deterministic sorted-key round-trip for every
  config + `dls_locked.json`), `test_dls_lock.py` (candidate name, one-byte hash tamper ->
  fails, missing source file -> fails, resolved-parameter drift -> fails, missing/invalid lock
  file -> fails via monkeypatched path, snapshot timestamp stable across repeated verification,
  verification never rewrites the lock file), `test_split_guard.py` (train/development allowed;
  validation denied without / allowed with authorization; frozen_test denied even with
  validation authorization; unknown/ambiguous split rejected; frozen-marker path rejected
  regardless of declared split; guard never touches filesystem content), `test_reference_hash.py`
  (PDF hash match + tamper detection), `test_srpdik_audit.py` (CLI pass on the real repo; usage
  error exit 2 on a bad `--dataset-v2-root`; exit 1 on monkeypatched lock/config/candidate/
  frozen-guard failures, never by mutating the real repo's files; pass/fail against a real
  throwaway Dataset v2 scaffold in `tmp_path`).
- First `pytest tests/srpdik -q` run caught a real bug: `configs/srpdik/srpdik_observation.json`
  (and 5 other configs) had been hand-written with compact inline objects inside JSON arrays
  (e.g. `{"dim": 7, "name": "..."}` on one line), which does not byte-match
  `json.dumps(sort_keys=True, indent=2)`'s canonical expansion of nested objects -- a genuine
  "deterministic key order" violation, not a test bug. Fixed by reloading each config's parsed
  dict and rewriting it through `srpdik.config.write_srpdik_config` (the same canonical
  serializer every future writer should use), so the on-disk bytes now match what re-running the
  writer produces. Also had to re-normalize `configs/srpdik/dls_locked.json` a second time: an
  earlier ad hoc tamper-test-and-restore step (atomic task 5's manual verification) had restored
  the correct *content* but via a plain `json.dump` with no `indent`/`sort_keys`, flattening the
  file to one line; re-ran it through `write_srpdik_config` to restore canonical formatting
  without touching any hash/value.
- `pytest tests/srpdik -q`: **71 passed, 0 failed** (after the fix above).
- Wrote `docs/srpdik/SRPDIK_METHOD_SPEC.md` (Phase 1 traceability table: locked DLS, 36-D
  observation, 7-D action, one-shot scope, protected-data prohibition, frozen-test prohibition,
  PDF reference integrity, path resolution, audit CLI -- each row cites its config/source and
  test, status `CONFIGURED` or `PLANNED`, never "implemented").
- Full `pytest -q` launched in the background (the Phase 0 baseline took ~55 minutes); result to
  be recorded in `PHASE_STATUS.json`/`HANDOFF.md` once it completes, before declaring the Phase 1
  gate met.
- No dataset v1/v2 file modified by any of the above. No frozen_test accessed.

### Phase 1 gate check (session end)

- Full `pytest -q` completed: **864 passed, 0 failed, in 3251.97s (0:54:11)** -- exactly the
  Phase 0 baseline (793) plus the 71 new `tests/srpdik/*` tests; no regressions anywhere else in
  the repo.
- Final `python -m pipelines.run_srpdik_audit` re-run: all checks pass (repo/git state, PDF
  hash, 9 configs parse, DLS lock parses + source hashes + candidate name, Dataset v1
  immutability, frozen_test denied by default, required dependencies available).
- `git status --short`: unchanged from session start plus this session's own new, still-untracked
  srpdik paths -- no other file was touched. Per the git-safety protocol (dirty tree at session
  start, per `docs/srpdik/DECISIONS.md` #4's precedent), no branch was created and no commit was
  made; `commit_status = "skipped_dirty_tree"` recorded in `PHASE_STATUS.json`/`HANDOFF.md`.
- Gate conditions verified: scaffold exists; configs parse; DLS lock verifies; split guard
  passes; audit CLI passes; targeted tests pass (71/71); full pytest passes (864/864); Dataset
  v1 unmodified (checksum-manifest recheck clean); Dataset v2 unmodified (no v2 root was ever
  written to); DLS source unmodified (hash-verified); frozen_test never accessed; no
  generation/evaluation/training run at any point this session.
- `PHASE_STATUS.json` set to `phase_id: "1"`, `status: "complete"`, `next_phase: "1A"`,
  `next_atomic_task`: "analyze locked pure-DLS failure modes and define SRPDIK training-data
  strata" (per the governing prompt's completion instructions). Phase 1A itself was not started
  this session, per the prompt's explicit instruction not to proceed past the gate.
