"""Tests for pipelines.run_srpdik_audit: exit codes and fail-closed reporting.

Failure-path tests use monkeypatch to simulate a broken lock/config rather than tampering with
the real repo files on disk, so this suite never risks leaving the repo's actual
configs/srpdik/dls_locked.json (or any other real file) in a modified state if a test crashes
partway through.
"""

from srpdik.exceptions import DLSLockVerificationError, SRPDIKConfigError

from pipelines import run_srpdik_audit


def test_audit_passes_on_the_real_repo(capsys):
    code = run_srpdik_audit.main([])
    captured = capsys.readouterr()
    assert code == 0
    assert "[run_srpdik_audit] PASS" in captured.out


def test_audit_usage_error_on_nonexistent_dataset_v2_root(tmp_path):
    missing = tmp_path / "does_not_exist"
    code = run_srpdik_audit.main(["--dataset-v2-root", str(missing)])
    assert code == 2


def test_audit_fails_when_dls_lock_hash_check_fails(monkeypatch, capsys):
    def _boom(lock):
        raise DLSLockVerificationError("simulated hash mismatch for test")

    monkeypatch.setattr(run_srpdik_audit, "verify_source_hashes", _boom)
    code = run_srpdik_audit.main([])
    captured = capsys.readouterr()
    assert code == 1
    assert "FAIL" in captured.out or "FAIL" in captured.err


def test_audit_fails_when_configs_do_not_parse(monkeypatch):
    def _boom():
        raise SRPDIKConfigError("simulated config parse failure for test")

    monkeypatch.setattr(run_srpdik_audit, "build_srpdik_config_manifest", _boom)
    code = run_srpdik_audit.main([])
    assert code == 1


def test_audit_fails_when_candidate_name_check_fails(monkeypatch):
    def _boom(lock):
        raise DLSLockVerificationError("simulated candidate name mismatch for test")

    monkeypatch.setattr(run_srpdik_audit, "verify_candidate_name", _boom)
    code = run_srpdik_audit.main([])
    assert code == 1


def test_audit_fails_when_frozen_access_is_not_denied_by_default(monkeypatch):
    monkeypatch.setattr(run_srpdik_audit, "is_split_access_allowed", lambda split: True)
    code = run_srpdik_audit.main([])
    assert code == 1


def test_audit_passes_dataset_v2_root_check_with_a_real_scaffold(tmp_path):
    from dataset_v2.scaffold import create_dataset_v2_scaffold

    v2_root = tmp_path / "v2root"
    create_dataset_v2_scaffold(dataset_root=v2_root, master_seed=42)
    code = run_srpdik_audit.main(["--dataset-v2-root", str(v2_root)])
    assert code == 0


def test_audit_fails_dataset_v2_root_check_when_manifest_missing(tmp_path):
    empty_root = tmp_path / "empty_root"
    empty_root.mkdir()
    code = run_srpdik_audit.main(["--dataset-v2-root", str(empty_root)])
    assert code == 1
