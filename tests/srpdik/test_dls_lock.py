"""Tests for srpdik.dls_lock: schema/candidate/hash verification, fail-closed behavior."""

import copy
import json

import pytest

from srpdik.constants import DLS_LOCK_FILENAME, OFFICIAL_DLS_CANDIDATE_ID
from srpdik.dls_lock import (
    get_locked_candidate_config,
    load_dls_lock,
    verify_candidate_name,
    verify_dls_lock,
    verify_resolved_parameters_match_live_source,
    verify_source_hashes,
)
from srpdik.exceptions import DLSLockVerificationError
from srpdik.paths import srpdik_config_path


def test_real_lock_verifies_clean():
    lock = verify_dls_lock()
    assert lock["candidate_name"] == OFFICIAL_DLS_CANDIDATE_ID


def test_official_candidate_is_cand_D_pure_dls():
    lock = load_dls_lock()
    assert lock["candidate_name"] == "cand_D_pure_dls" == OFFICIAL_DLS_CANDIDATE_ID
    verify_candidate_name(lock)  # does not raise


def test_wrong_candidate_name_fails_closed():
    lock = copy.deepcopy(load_dls_lock())
    lock["candidate_name"] = "cand_A_adaptive_baseline"
    with pytest.raises(DLSLockVerificationError):
        verify_candidate_name(lock)


def test_one_byte_hash_change_fails_verification():
    lock = copy.deepcopy(load_dls_lock())
    a_file = next(iter(lock["source_code_files"]))
    original = lock["source_code_files"][a_file]
    flipped_char = "1" if original[0] == "0" else "0"
    lock["source_code_files"][a_file] = flipped_char + original[1:]
    with pytest.raises(DLSLockVerificationError) as excinfo:
        verify_source_hashes(lock)
    assert a_file in str(excinfo.value)


def test_missing_source_file_fails_closed():
    lock = copy.deepcopy(load_dls_lock())
    lock["source_code_files"]["kinematics/does_not_exist.py"] = "0" * 64
    with pytest.raises(DLSLockVerificationError):
        verify_source_hashes(lock)


def test_resolved_parameters_drift_fails_closed():
    lock = copy.deepcopy(load_dls_lock())
    lock["resolved_parameters"]["max_iterations"] = 999999
    with pytest.raises(DLSLockVerificationError):
        verify_resolved_parameters_match_live_source(lock)


def test_missing_required_field_fails_closed(tmp_path, monkeypatch):
    bad_lock = copy.deepcopy(load_dls_lock())
    del bad_lock["immutable"]
    bad_path = tmp_path / DLS_LOCK_FILENAME
    bad_path.write_text(json.dumps(bad_lock), encoding="utf-8")
    monkeypatch.setattr("srpdik.dls_lock.srpdik_config_path", lambda name: bad_path)
    with pytest.raises(DLSLockVerificationError):
        load_dls_lock()


def test_immutable_must_be_true(tmp_path, monkeypatch):
    bad_lock = copy.deepcopy(load_dls_lock())
    bad_lock["immutable"] = False
    bad_path = tmp_path / DLS_LOCK_FILENAME
    bad_path.write_text(json.dumps(bad_lock), encoding="utf-8")
    monkeypatch.setattr("srpdik.dls_lock.srpdik_config_path", lambda name: bad_path)
    with pytest.raises(DLSLockVerificationError):
        load_dls_lock()


def test_missing_lock_file_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr("srpdik.dls_lock.srpdik_config_path", lambda name: tmp_path / "missing.json")
    with pytest.raises(DLSLockVerificationError):
        load_dls_lock()


def test_invalid_json_fails_closed(tmp_path, monkeypatch):
    bad_path = tmp_path / DLS_LOCK_FILENAME
    bad_path.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr("srpdik.dls_lock.srpdik_config_path", lambda name: bad_path)
    with pytest.raises(DLSLockVerificationError):
        load_dls_lock()


def test_get_locked_candidate_config_matches_resolved_parameters():
    cfg = get_locked_candidate_config()
    lock = load_dls_lock()
    assert cfg == lock["resolved_parameters"]


def test_source_paths_are_repo_relative_not_sibling_dataset_v2_root():
    lock = load_dls_lock()
    for path in lock["source_code_files"]:
        assert not path.startswith("/"), path
        assert ":" not in path, path
        assert "mpdik_kassow_v2" not in path
    assert lock["source_config_relative_path"] in lock["source_code_files"]


def test_snapshot_timestamp_stable_across_repeated_verification():
    first = load_dls_lock()["snapshot_timestamp_utc"]
    verify_dls_lock()
    verify_dls_lock()
    second = load_dls_lock()["snapshot_timestamp_utc"]
    assert first == second


def test_verification_does_not_modify_the_lock_file():
    path = srpdik_config_path(DLS_LOCK_FILENAME)
    before = path.read_bytes()
    verify_dls_lock()
    after = path.read_bytes()
    assert before == after
