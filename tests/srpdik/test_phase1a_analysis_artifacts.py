"""Validator for the Phase 1A locked-DLS failure-mode analysis artifacts.

Checks structural/statistical sanity of the read-only analysis outputs (CSV/JSON), not the
underlying dev/val/frozen data itself. Does not open any dataset v1/v2 file, any frozen_test
path, or any protected field -- it only parses the analysis artifacts this repo already
produced under docs/srpdik/.
"""

import csv
import json

import pytest

from srpdik.paths import srpdik_docs_dir

FAILURE_TABLE = "srpdik_dls_failure_mode_table.csv"
WAYPOINT0_TABLE = "srpdik_waypoint0_analysis.csv"
BASELINE_SUMMARY = "srpdik_dls_baseline_summary.json"
ANALYSIS_MD = "SRPDIK_DLS_BASELINE_FAILURE_ANALYSIS.md"
STRATA_MD = "SRPDIK_TRAINING_STRATA_SPEC.md"

PROTECTED_FIELD_NAMES = {
    "q_reference",
    "q_reference_start",
    "q_source_reference",
    "q_target_reference",
    "position_reconstruction_error_m",
    "orientation_reconstruction_error_rad",
    "waypoint_reachable",
}

RATE_COLUMNS_SUFFIXES = ("_rate", "_share")
NA = "not_available"


def _read_csv_rows(filename):
    path = srpdik_docs_dir() / filename
    assert path.is_file(), f"missing artifact: {path}"
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _read_json(filename):
    path = srpdik_docs_dir() / filename
    assert path.is_file(), f"missing artifact: {path}"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _is_float(value):
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _no_absolute_paths(text):
    lowered = text.lower()
    assert "d:\\" not in lowered
    assert "d:/" not in lowered
    assert "c:\\users" not in lowered
    assert "/d/data/hoang_anh" not in lowered


def _no_protected_keys(text):
    lowered = text.lower()
    for name in PROTECTED_FIELD_NAMES:
        assert name.lower() not in lowered, f"protected field leaked into artifact: {name}"


# ---------------------------------------------------------------------------
# Failure-mode table
# ---------------------------------------------------------------------------


def test_failure_mode_table_parses_and_has_rows():
    rows = _read_csv_rows(FAILURE_TABLE)
    assert len(rows) > 0


def test_failure_mode_table_no_absolute_paths_or_protected_keys():
    path = srpdik_docs_dir() / FAILURE_TABLE
    text = path.read_text(encoding="utf-8")
    _no_absolute_paths(text)
    _no_protected_keys(text)


def test_failure_mode_table_no_raw_frozen_per_sample_source():
    rows = _read_csv_rows(FAILURE_TABLE)
    for row in rows:
        ref = row.get("source_reference", "")
        if row.get("split") == "frozen_test":
            # frozen rows may only cite the published release aggregate, never a per-sample path.
            assert "eval_frozen/frozen_test" not in ref
            assert "final_dls_summary.json" in ref or ref == NA


def test_failure_mode_table_rates_in_unit_interval():
    rows = _read_csv_rows(FAILURE_TABLE)
    rate_cols = [c for c in rows[0].keys() if c.endswith("_rate") and "streak" not in c]
    for row in rows:
        for col in rate_cols:
            val = row[col]
            if val == NA:
                continue
            f = float(val)
            assert -1e-9 <= f <= 1.0 + 1e-9, f"{col}={val} out of [0,1] in row {row}"


def test_failure_mode_table_counts_non_negative():
    rows = _read_csv_rows(FAILURE_TABLE)
    count_cols = [c for c in rows[0].keys() if c.endswith("_count")]
    for row in rows:
        for col in count_cols:
            val = row[col]
            if val == NA:
                continue
            assert float(val) >= 0, f"{col}={val} negative in row {row}"


def test_failure_mode_table_success_numerator_denominator_consistent():
    rows = _read_csv_rows(FAILURE_TABLE)
    for row in rows:
        solve_count = row["solve_count"]
        if solve_count == NA:
            continue
        n = float(solve_count)
        for tier in ("coarse", "standard", "strict"):
            count_col = f"success_{tier}_count"
            rate_col = f"success_{tier}_rate"
            count_val, rate_val = row[count_col], row[rate_col]
            if count_val == NA or rate_val == NA or n == 0:
                continue
            expected_rate = float(count_val) / n
            assert abs(expected_rate - float(rate_val)) < 1e-6, (
                f"{row.get('result_type')}/{row.get('split')}/{row.get('group')}: "
                f"{count_col}={count_val}, {rate_col}={rate_val}, solve_count={n}"
            )


def test_failure_mode_table_no_duplicate_group_rows():
    rows = _read_csv_rows(FAILURE_TABLE)
    keys = [
        (r["result_type"], r["split"], r["group"], r["method"], r["source_type"]) for r in rows
    ]
    assert len(keys) == len(set(keys)), "duplicate (result_type, split, group, method, source_type) row found"


def test_failure_mode_table_deterministic_row_order():
    rows = _read_csv_rows(FAILURE_TABLE)
    keys = [
        (r["result_type"], r["split"], r["group"], str(r["method"]), str(r["source_type"]))
        for r in rows
    ]
    assert keys == sorted(keys)


def test_failure_mode_table_dls_candidate_matches_lock():
    from srpdik.dls_lock import load_dls_lock

    # the failure table itself doesn't repeat the candidate name per row (it's implicit to the
    # whole artifact, recorded once in the baseline summary); this just confirms the lock this
    # analysis was built against is still the one currently on disk.
    lock = load_dls_lock()
    assert lock["candidate_name"] == "cand_D_pure_dls"


# ---------------------------------------------------------------------------
# Waypoint-0 table
# ---------------------------------------------------------------------------


def test_waypoint0_table_parses_and_has_rows():
    rows = _read_csv_rows(WAYPOINT0_TABLE)
    assert len(rows) > 0


def test_waypoint0_table_no_absolute_paths_or_protected_keys():
    path = srpdik_docs_dir() / WAYPOINT0_TABLE
    text = path.read_text(encoding="utf-8")
    _no_absolute_paths(text)
    _no_protected_keys(text)


def test_waypoint0_table_rates_in_unit_interval():
    rows = _read_csv_rows(WAYPOINT0_TABLE)
    rate_cols = [c for c in rows[0].keys() if c.endswith("_rate")]
    for row in rows:
        for col in rate_cols:
            val = row[col]
            if val == NA or val == "":
                continue
            f = float(val)
            assert -1e-9 <= f <= 1.0 + 1e-9, f"{col}={val} out of [0,1] in row {row}"


def test_waypoint0_table_counts_non_negative():
    rows = _read_csv_rows(WAYPOINT0_TABLE)
    for row in rows:
        val = row["number_of_trials"]
        assert float(val) >= 0


def test_waypoint0_table_no_duplicate_rows():
    rows = _read_csv_rows(WAYPOINT0_TABLE)
    keys = [(r["split"], r["difficulty"], r["method"]) for r in rows]
    assert len(keys) == len(set(keys))


def test_waypoint0_table_deterministic_row_order():
    rows = _read_csv_rows(WAYPOINT0_TABLE)
    keys = [(r["split"], r["difficulty"], r["method"]) for r in rows]
    assert keys == sorted(keys)


def test_waypoint0_table_no_raw_frozen_source():
    rows = _read_csv_rows(WAYPOINT0_TABLE)
    for row in rows:
        assert row["split"] != "frozen_test"
        assert "eval_frozen/frozen_test" not in row.get("source_reference", "")


# ---------------------------------------------------------------------------
# Baseline summary JSON
# ---------------------------------------------------------------------------


def test_baseline_summary_parses():
    data = _read_json(BASELINE_SUMMARY)
    for key in (
        "schema_version",
        "analysis_version",
        "candidate_name",
        "dls_lock_hash",
        "official_result_sources",
        "official_metrics",
        "dominant_failure_mode",
        "waypoint0_findings",
        "joint_limit_and_singularity_findings",
        "training_strata",
        "unknowns",
        "data_access_audit",
    ):
        assert key in data, f"missing key: {key}"


def test_baseline_summary_candidate_matches_lock():
    from srpdik.dls_lock import load_dls_lock

    data = _read_json(BASELINE_SUMMARY)
    lock = load_dls_lock()
    assert data["candidate_name"] == lock["candidate_name"] == "cand_D_pure_dls"


def test_baseline_summary_no_absolute_paths_or_protected_keys():
    path = srpdik_docs_dir() / BASELINE_SUMMARY
    text = path.read_text(encoding="utf-8")
    _no_absolute_paths(text)
    _no_protected_keys(text)


def test_baseline_summary_data_access_audit_all_false_except_public_summary():
    data = _read_json(BASELINE_SUMMARY)
    audit = data["data_access_audit"]
    assert audit["raw_frozen_accessed"] is False
    assert audit["frozen_public_summary_used"] is True
    assert audit["protected_data_accessed"] is False
    assert audit["dataset_v1_modified"] is False
    assert audit["dataset_v2_modified"] is False
    assert audit["dls_source_modified"] is False
    assert audit["evaluation_rerun"] is False
    assert audit["training_run"] is False


def test_baseline_summary_training_strata_sampling_shares_sum_to_one():
    data = _read_json(BASELINE_SUMMARY)
    strata = data["training_strata"]
    assert len(strata) >= 8
    total = sum(s["recommended_sampling_share"] for s in strata)
    assert abs(total - 1.0) < 1e-6
    assert abs(data["training_strata_sampling_share_sum"] - 1.0) < 1e-6


def test_baseline_summary_training_strata_priorities_unique():
    data = _read_json(BASELINE_SUMMARY)
    priorities = [s["priority"] for s in data["training_strata"]]
    assert priorities == sorted(priorities)
    assert len(priorities) == len(set(priorities))


def test_baseline_summary_success_rate_reconciliation_matches_failure_table():
    data = _read_json(BASELINE_SUMMARY)
    rows = _read_csv_rows(FAILURE_TABLE)
    frozen_row = next(
        r
        for r in rows
        if r["result_type"] == "point_ik" and r["split"] == "frozen_test"
    )
    assert abs(float(frozen_row["success_standard_rate"]) - data["official_metrics"]["point_ik"]["frozen_test"]["success_standard"]) < 1e-9


def test_baseline_summary_unknowns_include_h1_vs_h2():
    data = _read_json(BASELINE_SUMMARY)
    joined = " ".join(data["unknowns"])
    assert "H1" in joined and "H2" in joined
    assert data["waypoint0_findings"]["h1_vs_h2_conclusion"] == "UNKNOWN_H1_VS_H2"


# ---------------------------------------------------------------------------
# Markdown docs exist and cite no raw frozen / protected content
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", [ANALYSIS_MD, STRATA_MD])
def test_markdown_doc_exists_and_is_nonempty(filename):
    path = srpdik_docs_dir() / filename
    assert path.is_file()
    assert len(path.read_text(encoding="utf-8")) > 500


def test_analysis_markdown_declares_data_access_audit():
    path = srpdik_docs_dir() / ANALYSIS_MD
    text = path.read_text(encoding="utf-8")
    assert "raw_frozen_accessed=false" in text
    assert "training_run=false" in text
    assert "evaluation_rerun=false" in text
