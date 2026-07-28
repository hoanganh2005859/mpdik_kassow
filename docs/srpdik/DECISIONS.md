# SR-PPO-DLS — Locked Decisions

Only decisions that are locked. Not a log — see `SRPDIK_IMPLEMENTATION_LOG.md` for that.

1. **Naming override**: every new package/directory/file for this method uses the name
   `srpdik`, not the PDF's own proposed `sr_ppo_dls` / `mpdik_kassow.sr_ppo_dls`. Applies to all
   future code (Phase C onward). Docs already follow this (`docs/srpdik/`).
2. **Dedicated directory**: `docs/srpdik/` holds all srpdik documentation. Future srpdik code
   lives under a dedicated top-level `srpdik/` directory at repo root (not inside
   `kinematics/`, `evaluation_v2/`, `algorithms/`, etc.) — mirrors PDF §12's proposed layout
   with names substituted per decision 1. Exact subpackage layout is finalized in Phase C, not
   this phase.
3. **PDF text extraction path**: kept literally as instructed
   (`srpdik/docs/srpdik/references/...txt`) AND duplicated to the mandatory Phase-0 output path
   (`docs/srpdik/references/...txt`) since the two instructions in this prompt disagreed on
   location. `docs/srpdik/references/` is the canonical path referenced by all other srpdik
   docs going forward.
4. **No branch created this phase**: working tree was dirty at session start
   (`SR_PPO_DLS_KR810_Theory_and_Dataset_Application.pdf` and
   `docs/srpdik/DLS_TRAJECTORY_PLOT_DIAGNOSIS.md` untracked, pre-existing). Per the token-safe
   protocol's git rule, a dirty tree means: no branch creation, no commit, docs-only if no
   conflict. `feature/srpdik` branch creation is deferred to whoever starts Phase A with a clean
   or user-approved tree.
5. **Locked DLS candidate**: `cand_D_pure_dls` (`evaluation_v2/candidate_configs.py`). SR-PPO-DLS
   must never modify `kinematics/dls_solver.py`, `kinematics/adaptive_damping.py`,
   `kinematics/joint_limit_utils.py`, or `evaluation_v2/candidate_configs.py`. It only changes
   the seed passed into `solve_dls_until_converged`.
6. **Dataset v2 data root is outside the repo**: actual Point-IK/trajectory data lives in
   sibling directories under `D:\data\hoang_anh\` (e.g. `mpdik_kassow_v2_work`,
   `mpdik_kassow_v2_eval_devval`, `mpdik_kassow_v2_eval_frozen`,
   `KR810_Tier0_Tier4_Dataset_v2.0.0`). All srpdik dataset access takes an explicit
   `dataset_root` argument; no hardcoded path, no CWD assumption.
7. **Permanently out of scope** (unless the user explicitly re-scopes): Multistep PPO (PPO
   re-invoked per DLS iteration or per waypoint), MAPPO, dynamics/actuator/controller/torque/
   collision/payload/compliance/backlash/sensor-noise/TCP-calibration work, real-robot or ISO
   certification claims. Source: PDF §1/§2.2/§9.6/§14.6 and CLAUDE.md project scope.
8. **This phase (Phase 0) implements no algorithm or training code** — only PDF ingestion,
   audit, and handoff docs, per this prompt's explicit instruction.
9. **Baseline success-rate figures need reconciliation before being quoted in any report** —
   **RESOLVED in Phase 1A**. PDF p.1's "≈95.08%" and `docs/CHATGPT_DLS_CURRENT_STATE_BRIEF.md`'s
   "0.951 frozen" are the same underlying number,
   `final_dls_summary.json::frozen_test.point_ik.success_standard = 0.9508333333333333`
   (= 3423/3600), displayed at different rounding precision — not a real discrepancy.
   Development = 0.9633333333333334 (1156/1200), validation = 0.9625 (1155/1200), both
   cross-checked exactly against `point_metrics.csv::group=overall,success_count_standard`. Full
   reconciliation table: `docs/srpdik/SRPDIK_DLS_BASELINE_FAILURE_ANALYSIS.md` §3.
10. **Phase renumbering (explicit user override, this session)**: the Phase 0 handoff
    (`HANDOFF.md`, `PHASE_STATUS.json`, `NEXT_COMMANDS.md` PROMPT 1) had queued the locked
    `SRPDIK_IMPLEMENTATION_PLAN.md` ordering `0 → A (read-only frozen failure-mode/success-rate
    reconciliation) → B (training-stream generator) → C (baseline cache) → D (env/observation/
    action/safety) → ...` as the next atomic task. This session's governing prompt instead
    defines a new **"Phase 1 — Scaffold + locked pure-DLS snapshot"** that builds the `srpdik/`
    package scaffold, `configs/srpdik/*.json`, the DLS lock (`dls_locked.json` +
    `srpdik/dls_lock.py`), a split guard, and an audit CLI — none of which is "Phase A" — and
    defers the Phase-A-style failure-mode analysis to a new **"Phase 1A"** that runs *after* the
    scaffold, reversing the locked plan's analysis-before-code order. Presented this conflict to
    the user directly (not inferred); user explicitly chose "proceed with new Phase 1" over
    "do locked Phase A first." Effective immediately: **"Phase 1"/"Phase 1A"/... is the active
    phase sequence for this method**, superseding the old `0/A/B/C/...` letter sequence in
    `SRPDIK_IMPLEMENTATION_PLAN.md`. That file's phase table is retained as a historical record
    of the original Phase-0-era plan, not as the authoritative next-step source; `PHASE_STATUS.json`
    and `HANDOFF.md` are authoritative for current phase/task going forward. No code, config, or
    algorithm behavior decision from the original plan (DLS lock target = `cand_D_pure_dls`,
    36-D observation, 7-D residual action, paired baseline, leakage policy, out-of-scope list,
    etc.) is changed by this renumbering — only phase *order/naming* changes.
11. **Phase 1A validation-split read access, interpreted as explicitly authorized** (this
    session). `configs/srpdik/srpdik_data.json::splits.validation.access =
    "requires_explicit_authorization"` gates validation-split reads behind explicit authorization.
    Phase 1A's governing prompt itself lists "validation summaries" in its §3 allowed-source list
    for read-only failure-mode analysis. This is treated as that explicit authorization for
    Phase 1A's read-only analysis only (`point_metrics.csv`, `point_failures.csv`,
    `trajectory_trial_summaries.csv`, `waypoint_results.csv`, `trajectory_metrics.csv` under
    `mpdik_kassow_v2_eval_devval/validation/cand_D_pure_dls/`) — it does not authorize validation
    access for any other purpose (generator design, threshold tuning, model selection), which
    remains gated by the same config flag. `frozen_test` remains fully denied throughout; see
    `docs/srpdik/SRPDIK_DLS_BASELINE_FAILURE_ANALYSIS.md` §1.
