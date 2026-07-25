"""Targeted tests for Phase 8B frozen_test access: the append-only ledger (access_count must stay
1), the frozen-only public export (isolation + split scoping), and the orchestrator's explicit
``allow_frozen`` opt-in (default-False guard unchanged from Phase 8A; frozen_test reachable only
with the flag).

Dataset-dependent tests are skipped automatically if the Dataset v2 working root is not present
(mirrors ``tests/test_dataset_v2_eval_harness.py``).
"""

import os
from pathlib import Path

import pytest

from evaluation_v2.frozen_ledger import FrozenAccessLimitExceeded, open_or_resume_frozen_access, read_ledger

WORK_ROOT = Path(os.environ.get("MPDIK_V2_WORK_ROOT", r"D:\data\hoang_anh\mpdik_kassow_v2_work"))


# ---- ledger (pure logic, no dataset needed) ------------------------------------------------
def _open(ledger_path, run_id):
    return open_or_resume_frozen_access(
        ledger_path, run_id=run_id, purpose="official DLS frozen baseline",
        evaluation_lock_commit="cand_D_pure_dls", config_hash="cfg0", dataset_hash="ds0",
        candidate_id="cand_D_pure_dls", command="test", environment_fingerprint="env0",
    )


def test_ledger_first_open_sets_access_count_1(tmp_path):
    ledger_path = tmp_path / "frozen_access_ledger.json"
    ledger = _open(ledger_path, "run_A")
    assert ledger["access_count"] == 1
    assert ledger["events"][-1]["status"] == "opened_for_official_run"


def test_ledger_resume_same_run_id_does_not_bump_count(tmp_path):
    ledger_path = tmp_path / "frozen_access_ledger.json"
    _open(ledger_path, "run_A")
    ledger = _open(ledger_path, "run_A")
    assert ledger["access_count"] == 1
    assert ledger["events"][-1]["status"] == "resumed_for_official_run"
    assert len(ledger["events"]) == 2  # append-only: both events retained


def test_ledger_refuses_second_distinct_run_id(tmp_path):
    ledger_path = tmp_path / "frozen_access_ledger.json"
    _open(ledger_path, "run_A")
    with pytest.raises(FrozenAccessLimitExceeded):
        _open(ledger_path, "run_B")
    # Refused attempt must not have been appended.
    ledger = read_ledger(ledger_path)
    assert ledger["access_count"] == 1
    assert {e["run_id"] for e in ledger["events"]} == {"run_A"}


# ---- orchestrator allow_frozen guard (pure logic: raises before touching any root) ----------
def test_run_evaluation_rejects_frozen_split_by_default(tmp_path):
    from evaluation_v2.candidate_configs import candidate_by_id
    from evaluation_v2.orchestrator import run_evaluation

    with pytest.raises(ValueError, match="allow_frozen"):
        run_evaluation(
            tmp_path / "ds", tmp_path / "pub", tmp_path / "out",
            candidate_by_id("cand_D_pure_dls"), splits=("frozen_test",),
        )


def test_run_evaluation_still_rejects_unknown_split_with_allow_frozen(tmp_path):
    from evaluation_v2.candidate_configs import candidate_by_id
    from evaluation_v2.orchestrator import run_evaluation

    with pytest.raises(ValueError):
        run_evaluation(
            tmp_path / "ds", tmp_path / "pub", tmp_path / "out",
            candidate_by_id("cand_D_pure_dls"), splits=("bogus_split",), allow_frozen=True,
        )


# ---- frozen export isolation (dataset-dependent) --------------------------------------------
pytestmark_dataset = pytest.mark.skipif(
    not (WORK_ROOT / "DATASET_MANIFEST.json").is_file(),
    reason=f"Dataset v2 working root not available at {WORK_ROOT}",
)


@pytestmark_dataset
def test_frozen_export_contains_only_frozen_split_no_protected_fields(tmp_path):
    from evaluation_v2.protected_guard import find_protected_fields
    from evaluation_v2.public_export import export_frozen_public_only
    from utils.npz_utils import load_npz

    frozen_root = tmp_path / "frozen_public"
    summary = export_frozen_public_only(WORK_ROOT, frozen_root, overwrite=True)
    assert summary["splits"] == ["frozen_test"]
    assert summary["point_ik"]["frozen_test"] == 3600
    assert summary["trials"]["frozen_test"] == 210

    point = load_npz(frozen_root / "tier1_point_ik" / "frozen_test.npz")
    assert find_protected_fields(point.keys()) == []
    assert "q_target_reference" not in point

    trials = load_npz(frozen_root / "trials" / "frozen_test.npz")
    assert find_protected_fields(trials.keys()) == []

    # No development/validation data leaked into the frozen-only root.
    assert not (frozen_root / "tier1_point_ik" / "development.npz").exists()
    assert not (frozen_root / "tier1_point_ik" / "validation.npz").exists()
    for traj_file in (frozen_root / "trajectories").rglob("*.npz"):
        arrays = load_npz(traj_file)
        assert find_protected_fields(arrays.keys()) == []
        assert "q_reference" not in arrays
