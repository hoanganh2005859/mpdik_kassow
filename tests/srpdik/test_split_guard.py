"""Tests for srpdik.data.split_guard: fail-closed dataset split access policy."""

import pytest

from srpdik.data.split_guard import assert_split_access_allowed, is_split_access_allowed
from srpdik.exceptions import SplitAccessDenied


def test_train_allowed():
    assert assert_split_access_allowed("train") == "train"
    assert assert_split_access_allowed("training") == "train"


def test_development_allowed():
    assert assert_split_access_allowed("development") == "development"
    assert assert_split_access_allowed("dev") == "development"


def test_validation_requires_explicit_authorization():
    with pytest.raises(SplitAccessDenied):
        assert_split_access_allowed("validation")
    assert assert_split_access_allowed("validation", validation_authorized=True) == "validation"


def test_frozen_test_always_denied_even_with_validation_authorization():
    with pytest.raises(SplitAccessDenied):
        assert_split_access_allowed("frozen_test")
    with pytest.raises(SplitAccessDenied):
        assert_split_access_allowed("frozen_test", validation_authorized=True)


def test_unknown_split_rejected():
    with pytest.raises(SplitAccessDenied):
        assert_split_access_allowed("bogus_split_name")


def test_ambiguous_alias_rejected():
    with pytest.raises(SplitAccessDenied):
        assert_split_access_allowed("test")
    with pytest.raises(SplitAccessDenied):
        assert_split_access_allowed("frozen")


def test_empty_split_name_rejected():
    with pytest.raises(SplitAccessDenied):
        assert_split_access_allowed("")
    with pytest.raises(SplitAccessDenied):
        assert_split_access_allowed("   ")


def test_path_with_frozen_marker_rejected_regardless_of_declared_split():
    with pytest.raises(SplitAccessDenied):
        assert_split_access_allowed(
            "development",
            path=r"D:\data\hoang_anh\mpdik_kassow_v2_eval_frozen\point_ik.npz",
        )


def test_is_split_access_allowed_non_raising_wrapper():
    assert is_split_access_allowed("train") is True
    assert is_split_access_allowed("development") is True
    assert is_split_access_allowed("validation") is False
    assert is_split_access_allowed("frozen_test") is False
    assert is_split_access_allowed("bogus") is False


def test_guard_never_opens_split_content(tmp_path):
    # A path argument pointing at a nonexistent file must not raise a filesystem error -- the
    # guard only reasons about the string, never opens/reads it.
    missing = tmp_path / "does_not_exist_at_all.npz"
    assert assert_split_access_allowed("development", path=missing) == "development"
