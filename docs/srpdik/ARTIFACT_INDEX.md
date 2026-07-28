# SR-PPO-DLS — Artifact Index

| Path | Type | Status | Checksum |
|---|---|---|---|
| `docs/srpdik/references/SR_PPO_DLS_KR810_Theory_and_Dataset_Application.pdf` | source PDF (copy of repo-root original) | final, do not edit | SHA256 `b9a9fe0c65719ccbcfb7cf92bbea4b72b016d6a1c43f91892614bdfad0c96395` |
| `SR_PPO_DLS_KR810_Theory_and_Dataset_Application.pdf` | source PDF (original, repo root, untracked) | final, do not edit | same as above (byte-identical copy) |
| `docs/srpdik/references/SR_PPO_DLS_KR810_Theory_and_Dataset_Application.txt` | extracted text (pdftotext -layout, no OCR) | final | not hashed; 1262 lines / ~7869 words, regenerate via `pdftotext -layout <pdf> <txt>` if PDF ever changes |
| `srpdik/docs/srpdik/references/SR_PPO_DLS_KR810_Theory_and_Dataset_Application.txt` | duplicate of extracted text (literal path from prompt step A.6) | final | byte-identical to the `docs/srpdik/references/...txt` copy |
| `docs/srpdik/SRPDIK_REFERENCE_REQUIREMENTS.md` | requirements map (PDF → implementation) | final for Phase 0 | n/a |
| `docs/srpdik/SRPDIK_SOURCE_MAP.md` | compact repo source map (57 lines) | final for Phase 0 | n/a |
| `docs/srpdik/SRPDIK_IMPLEMENTATION_PLAN.md` | phased implementation plan | final for Phase 0 | n/a |
| `docs/srpdik/SRPDIK_IMPLEMENTATION_LOG.md` | append-only implementation log | open (Phase 0 entry only) | n/a |
| `docs/srpdik/HANDOFF.md` | current session handoff | updated each atomic task | n/a |
| `docs/srpdik/DECISIONS.md` | locked decisions | updated when a new decision locks | n/a |
| `docs/srpdik/ARTIFACT_INDEX.md` | this file | updated when a new artifact appears | n/a |
| `docs/srpdik/NEXT_COMMANDS.md` | exact next commands | updated each atomic task | n/a |
| `docs/srpdik/PHASE_STATUS.json` | machine-readable phase status | updated each atomic task | n/a |
| `docs/srpdik/DLS_TRAJECTORY_PLOT_DIAGNOSIS.md` | pre-existing, unrelated to this phase's work | untouched (was already untracked before this session) | n/a |
| `srpdik/__init__.py`, `constants.py`, `exceptions.py`, `paths.py`, `config.py`, `manifests.py` | Phase 1 package scaffold | final for atomic task 1 | n/a |
| `srpdik/dls_lock.py` | Phase 1 DLS lock module | placeholder (atomic task 1); real implementation is atomic task 3 | n/a |
| `srpdik/data/__init__.py`, `srpdik/data/split_guard.py` | Phase 1 data-access scaffold | `split_guard.py` placeholder (atomic task 1); real implementation is atomic task 4 | n/a |
| `srpdik/features/__init__.py`, `srpdik/policy/__init__.py`, `srpdik/envs/__init__.py`, `srpdik/training/__init__.py`, `srpdik/evaluation/__init__.py`, `srpdik/kaggle/__init__.py` | Phase 1 empty subpackage scaffold | final for atomic task 1 (no behavior planned until later phases) | n/a |
| `configs/srpdik/`, `tests/srpdik/`, `notebooks/srpdik/`, `results/srpdik/` | Phase 1 directory scaffold | created, mostly empty (`.gitkeep`); configs/tests populated in later atomic tasks | n/a |
| `configs/srpdik/srpdik_{method,observation,action,safety,reward,training,curriculum,evaluation,data}.json` | Phase 1 method configs (atomic task 2) | final for Phase 1; structural lock only, most numeric values marked dev-tuned/later-phase | n/a (hashes recomputable via `srpdik.manifests.build_srpdik_config_manifest()`) |
| `configs/srpdik/dls_locked.json` | Phase 1 locked pure-DLS snapshot (atomic task 3) | final, immutable; do not edit without a new explicit re-lock decision | source hashes embedded in the file itself; verify via `srpdik.dls_lock.verify_dls_lock()` |
| `srpdik/dls_lock.py` | Phase 1 DLS lock loader/verifier (atomic task 3) | final for Phase 1 | n/a |
| `srpdik/data/split_guard.py` | Phase 1 split access guard (atomic task 4) | final for Phase 1 | n/a |
| `pipelines/run_srpdik_audit.py` | Phase 1 read-only audit CLI (atomic task 5) | final for Phase 1 | n/a |
| `tests/srpdik/test_{paths,configs,dls_lock,split_guard,reference_hash,srpdik_audit}.py` | Phase 1 test suite | final for Phase 1; 71 tests passing | n/a |
| `docs/srpdik/SRPDIK_METHOD_SPEC.md` | Phase 1 PDF-requirement traceability table | final for Phase 1 | n/a |

No dataset v1 or v2 generated artifacts were created, modified, or read-written this phase.
No training run occurred. No frozen_test split was accessed.

## Phase 1A (locked DLS failure-mode analysis and training-data strata)

| Path | Type | Status | Checksum |
|---|---|---|---|
| `docs/srpdik/SRPDIK_DLS_BASELINE_FAILURE_ANALYSIS.md` | Phase 1A failure-mode analysis (13 sections) | final for Phase 1A | n/a |
| `docs/srpdik/SRPDIK_TRAINING_STRATA_SPEC.md` | Phase 1A training-data strata design (8 strata) | final for Phase 1A; sampling shares PROPOSED, not locked | n/a |
| `docs/srpdik/srpdik_dls_failure_mode_table.csv` | Phase 1A failure-mode table (point-IK + trajectory, dev/val per-group, frozen aggregate-only rows) | final for Phase 1A; 36 rows | n/a (validated by `tests/srpdik/test_phase1a_analysis_artifacts.py`) |
| `docs/srpdik/srpdik_waypoint0_analysis.csv` | Phase 1A waypoint-0 analysis (12 rows: 2 splits x 3 difficulties x 2 methods) | final for Phase 1A | n/a |
| `docs/srpdik/srpdik_dls_baseline_summary.json` | Phase 1A machine-readable rollup (metrics, dominant failure mode, waypoint-0 findings, training strata, unknowns, data-access audit) | final for Phase 1A | n/a |
| `tests/srpdik/test_phase1a_analysis_artifacts.py` | Phase 1A artifact validator (27 tests) | final for Phase 1A | n/a |
| `docs/srpdik/DECISIONS.md` | updated: #9 marked resolved, #11 added | updated this phase | n/a |
| `docs/srpdik/SRPDIK_IMPLEMENTATION_LOG.md` | appended: Phase 1A entry | updated this phase | n/a |

No dataset v1 or v2 file was created, modified, or read-written this phase. No `frozen_test` raw
per-sample file was opened (only the published `final_dls_summary.json` aggregate and the frozen
access ledger/report). No DLS solver/generator/evaluation code was run. No training run occurred.
