"""Tests for srpdik.config / srpdik.manifests: parsing, metadata, and path/leakage policy."""

import json

import pytest

from srpdik import constants
from srpdik.config import (
    assert_config_policy,
    assert_required_metadata,
    load_srpdik_config,
    write_srpdik_config,
)
from srpdik.exceptions import SRPDIKConfigError
from srpdik.manifests import build_srpdik_config_manifest
from srpdik.paths import srpdik_config_dir


def test_all_srpdik_configs_parse():
    manifest = build_srpdik_config_manifest()
    assert set(manifest) == set(constants.CONFIG_FILENAMES)


@pytest.mark.parametrize("filename", constants.CONFIG_FILENAMES)
def test_required_metadata_fields_present(filename):
    config = load_srpdik_config(filename)
    for field in ("schema_version", "method_version", "description"):
        assert field in config, f"{filename} missing {field}"


@pytest.mark.parametrize("filename", constants.CONFIG_FILENAMES)
def test_config_passes_path_and_leakage_policy(filename):
    config = load_srpdik_config(filename)
    assert_config_policy(config, context=filename)  # must not raise


def test_observation_dims_sum_to_36():
    config = load_srpdik_config("srpdik_observation.json")
    assert config["observation_dim"] == constants.OBSERVATION_DIM
    assert sum(field["dim"] for field in config["fields"]) == constants.OBSERVATION_DIM


def test_action_dim_matches_constant():
    config = load_srpdik_config("srpdik_action.json")
    assert config["action_dim"] == constants.ACTION_DIM


def test_rejects_missing_metadata():
    bad = {"schema_version": "1.0.0"}  # missing method_version, description
    with pytest.raises(SRPDIKConfigError):
        assert_required_metadata(bad, context="bad.json")


def test_rejects_windows_absolute_path_value():
    bad = {
        "schema_version": "1.0.0",
        "method_version": "0.1.0",
        "description": "x",
        "some_path": "D:\\data\\hoang_anh\\mpdik_kassow_v2_eval_frozen\\file.npz",
    }
    with pytest.raises(SRPDIKConfigError):
        assert_config_policy(bad, context="bad")


def test_rejects_posix_absolute_path_value():
    bad = {
        "schema_version": "1.0.0",
        "method_version": "0.1.0",
        "description": "x",
        "some_path": "/etc/passwd",
    }
    with pytest.raises(SRPDIKConfigError):
        assert_config_policy(bad, context="bad")


def test_rejects_protected_field_as_live_key():
    bad = {
        "schema_version": "1.0.0",
        "method_version": "0.1.0",
        "description": "x",
        "q_target_reference": "some/value",
    }
    with pytest.raises(SRPDIKConfigError):
        assert_config_policy(bad, context="bad")


def test_allows_protected_field_name_as_documentation_value():
    # Documenting the exclusion list (forbidden_fields) is required by the spec and must NOT be
    # rejected -- only a live field *key* would actually wire protected data in.
    good = {
        "schema_version": "1.0.0",
        "method_version": "0.1.0",
        "description": "x",
        "forbidden_fields": ["q_target_reference", "q_reference"],
    }
    assert_config_policy(good, context="good")  # must not raise


def test_missing_config_file_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("srpdik.config.srpdik_config_path", lambda name: tmp_path / name)
    with pytest.raises(SRPDIKConfigError):
        load_srpdik_config("does_not_exist.json")


def test_invalid_json_raises(tmp_path, monkeypatch):
    bad_path = tmp_path / "broken.json"
    bad_path.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr("srpdik.config.srpdik_config_path", lambda name: bad_path)
    with pytest.raises(SRPDIKConfigError):
        load_srpdik_config("broken.json")


def test_deterministic_key_order_round_trip():
    config_dir = srpdik_config_dir()
    for filename in list(constants.CONFIG_FILENAMES) + [constants.DLS_LOCK_FILENAME]:
        path = config_dir / filename
        original = path.read_text(encoding="utf-8")
        data = json.loads(original)
        rewritten = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
        assert rewritten == original, f"{filename} is not written with deterministic sorted key order"


def test_write_srpdik_config_is_deterministic_regardless_of_insertion_order(tmp_path):
    data = {"b": 1, "a": 2, "description": "x", "schema_version": "1.0.0", "method_version": "0.1.0"}
    reordered = dict(reversed(list(data.items())))
    path1 = tmp_path / "one.json"
    path2 = tmp_path / "two.json"
    write_srpdik_config(path1, data)
    write_srpdik_config(path2, reordered)
    assert path1.read_text(encoding="utf-8") == path2.read_text(encoding="utf-8")
