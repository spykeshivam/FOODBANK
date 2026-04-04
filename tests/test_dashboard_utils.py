"""Unit tests for services/dashboard_utils.py."""
import pandas as pd
import pytest

from services.dashboard_utils import (
    add_time_buckets,
    apply_date_range,
    ensure_datetime_series,
    find_column,
    parse_timestamp_series,
    parse_timestamps,
    resample_counts,
)


# ── parse_timestamp_series ─────────────────────────────────────────────────

def test_parse_timestamp_series_iso_format():
    s = pd.Series(["2024-01-15 10:30:00", "2024-03-01 09:00:00"])
    result = parse_timestamp_series(s)
    assert result.notna().all()


def test_parse_timestamp_series_us_format():
    s = pd.Series(["01/15/2024 10:30:00"])
    result = parse_timestamp_series(s)
    assert result.notna().all()


def test_parse_timestamp_series_dmy_format():
    s = pd.Series(["15/01/2024 10:30:00"])
    result = parse_timestamp_series(s)
    assert result.notna().all()


def test_parse_timestamp_series_mixed_formats():
    s = pd.Series(["2024-01-15 10:30:00", "01/20/2024 09:00:00"])
    result = parse_timestamp_series(s)
    assert result.notna().all()


def test_parse_timestamp_series_invalid_returns_nat():
    s = pd.Series(["not-a-date", "also-bad"])
    result = parse_timestamp_series(s)
    assert result.isna().all()


def test_parse_timestamp_series_none_input_returns_empty():
    result = parse_timestamp_series(None)
    assert len(result) == 0


def test_parse_timestamp_series_non_series_input():
    result = parse_timestamp_series(["2024-01-15 10:00:00"])
    assert result.notna().all()


# ── ensure_datetime_series ─────────────────────────────────────────────────

def test_ensure_datetime_series_already_datetime_is_returned():
    s = pd.to_datetime(pd.Series(["2024-01-15 10:00:00"]))
    result = ensure_datetime_series(s)
    assert pd.api.types.is_datetime64_any_dtype(result)


def test_ensure_datetime_series_converts_strings():
    s = pd.Series(["2024-01-15 10:00:00"])
    result = ensure_datetime_series(s)
    assert pd.api.types.is_datetime64_any_dtype(result)


def test_ensure_datetime_series_none_returns_empty():
    result = ensure_datetime_series(None)
    assert len(result) == 0


# ── parse_timestamps ───────────────────────────────────────────────────────

def test_parse_timestamps_adds_parsed_column():
    df = pd.DataFrame([{"Timestamp": "2024-01-15 10:00:00", "Username": "u1"}])
    result = parse_timestamps(df, "Timestamp", "ParsedLogin")
    assert "ParsedLogin" in result.columns
    assert result["ParsedLogin"].notna().all()


def test_parse_timestamps_missing_source_col_fills_nat():
    df = pd.DataFrame([{"Username": "u1"}])
    result = parse_timestamps(df, "Timestamp", "ParsedLogin")
    assert "ParsedLogin" in result.columns
    assert result["ParsedLogin"].isna().all()


def test_parse_timestamps_none_df_returns_empty():
    result = parse_timestamps(None, "Timestamp", "ParsedLogin")
    assert result.empty


def test_parse_timestamps_does_not_mutate_original():
    df = pd.DataFrame([{"Timestamp": "2024-01-15 10:00:00"}])
    parse_timestamps(df, "Timestamp", "ParsedLogin")
    assert "ParsedLogin" not in df.columns


# ── apply_date_range ───────────────────────────────────────────────────────

def _range_df():
    return pd.DataFrame([
        {"Username": "u1", "ParsedLogin": pd.Timestamp("2024-01-10")},
        {"Username": "u2", "ParsedLogin": pd.Timestamp("2024-02-15")},
        {"Username": "u3", "ParsedLogin": pd.Timestamp("2024-03-20")},
    ])


def test_apply_date_range_filters_inside_range():
    df = _range_df()
    result = apply_date_range(df, "ParsedLogin", "2024-01-01", "2024-02-28")
    assert len(result) == 2


def test_apply_date_range_no_start_date():
    df = _range_df()
    result = apply_date_range(df, "ParsedLogin", None, "2024-02-28")
    assert len(result) == 2


def test_apply_date_range_no_end_date():
    df = _range_df()
    result = apply_date_range(df, "ParsedLogin", "2024-02-01", None)
    assert len(result) == 2


def test_apply_date_range_start_after_end_swaps():
    df = _range_df()
    # Reversed dates should produce same result as the correct order
    result_normal = apply_date_range(df, "ParsedLogin", "2024-01-01", "2024-02-28")
    result_swapped = apply_date_range(df, "ParsedLogin", "2024-02-28", "2024-01-01")
    assert len(result_normal) == len(result_swapped)


def test_apply_date_range_empty_df_returns_empty():
    result = apply_date_range(pd.DataFrame(), "ParsedLogin", "2024-01-01", "2024-12-31")
    assert result.empty


def test_apply_date_range_missing_column_returns_empty():
    df = pd.DataFrame([{"Username": "u1"}])
    result = apply_date_range(df, "ParsedLogin", "2024-01-01", "2024-12-31")
    assert result.empty


def test_apply_date_range_none_df_returns_empty():
    result = apply_date_range(None, "ParsedLogin", "2024-01-01", "2024-12-31")
    assert result.empty


# ── add_time_buckets ───────────────────────────────────────────────────────

def _bucket_df():
    return pd.DataFrame([
        {"Username": "u1", "ParsedLogin": pd.Timestamp("2024-01-10")},
        {"Username": "u2", "ParsedLogin": pd.Timestamp("2024-01-17")},
        {"Username": "u3", "ParsedLogin": pd.Timestamp("2024-02-01")},
    ])


def test_add_time_buckets_daily_format():
    result = add_time_buckets(_bucket_df(), "ParsedLogin", "daily")
    assert "_bucket" in result.columns
    assert result["_bucket"].iloc[0] == "2024-01-10"


def test_add_time_buckets_weekly_contains_W():
    result = add_time_buckets(_bucket_df(), "ParsedLogin", "weekly")
    assert "_bucket" in result.columns
    assert "W" in result["_bucket"].iloc[0]


def test_add_time_buckets_monthly_format():
    result = add_time_buckets(_bucket_df(), "ParsedLogin", "monthly")
    assert "_bucket" in result.columns
    assert "2024-01" in result["_bucket"].iloc[0]


def test_add_time_buckets_empty_df_returns_bucket_column():
    result = add_time_buckets(pd.DataFrame(), "ParsedLogin", "daily")
    assert "_bucket" in result.columns


def test_add_time_buckets_missing_column_returns_na_bucket():
    df = pd.DataFrame([{"Username": "u1"}])
    result = add_time_buckets(df, "ParsedLogin", "daily")
    assert "_bucket" in result.columns


# ── resample_counts ────────────────────────────────────────────────────────

def _counts_df():
    return pd.DataFrame([
        {"Username": "u1", "ParsedLogin": pd.Timestamp("2024-01-10")},
        {"Username": "u2", "ParsedLogin": pd.Timestamp("2024-01-10")},
        {"Username": "u3", "ParsedLogin": pd.Timestamp("2024-02-01")},
    ])


def test_resample_counts_returns_dataframe_with_bucket_and_count():
    result = resample_counts(_counts_df(), "ParsedLogin", "daily")
    assert isinstance(result, pd.DataFrame)
    assert "bucket" in result.columns
    assert "count" in result.columns


def test_resample_counts_totals_match_rows():
    df = _counts_df()
    result = resample_counts(df, "ParsedLogin", "daily")
    assert result["count"].sum() == len(df)


def test_resample_counts_groups_correctly():
    df = _counts_df()
    result = resample_counts(df, "ParsedLogin", "daily")
    # 2024-01-10 has 2 rows
    jan_10 = result[result["bucket"] == "2024-01-10"]
    assert jan_10["count"].iloc[0] == 2


def test_resample_counts_empty_df_returns_empty():
    result = resample_counts(pd.DataFrame(), "ParsedLogin", "daily")
    assert result.empty


def test_resample_counts_none_returns_empty():
    result = resample_counts(None, "ParsedLogin", "daily")
    assert result.empty


def test_resample_counts_missing_column_returns_empty():
    df = pd.DataFrame([{"Username": "u1"}])
    result = resample_counts(df, "ParsedLogin", "daily")
    assert result.empty


def test_resample_counts_monthly_granularity():
    df = _counts_df()
    result = resample_counts(df, "ParsedLogin", "monthly")
    assert len(result) == 2  # Jan and Feb


def test_resample_counts_weekly_granularity():
    df = _counts_df()
    result = resample_counts(df, "ParsedLogin", "weekly")
    assert not result.empty


# ── find_column ────────────────────────────────────────────────────────────

def _df_with_cols(*cols):
    """Create a one-row DataFrame with the given columns.
    Note: find_column uses df.empty which is True for DataFrames
    with columns but no rows, so we always need at least one row.
    """
    return pd.DataFrame([{col: "value" for col in cols}])


def test_find_column_exact_match():
    df = _df_with_cols("Username", "First Name", "Surname")
    assert find_column(df, ["Username"]) == "Username"


def test_find_column_case_insensitive_match():
    df = _df_with_cols("username", "first name")
    assert find_column(df, ["Username"]) == "username"


def test_find_column_first_candidate_wins():
    df = _df_with_cols("Sex", "Gender")
    result = find_column(df, ["Sex", "Gender"])
    assert result == "Sex"


def test_find_column_fallback_to_second_candidate():
    df = _df_with_cols("Gender")
    result = find_column(df, ["Sex", "Gender"])
    assert result == "Gender"


def test_find_column_contains_match():
    df = _df_with_cols("How did you hear about us?")
    result = find_column(df, ["Referral Source", "How did you hear about us?"], contains=True)
    assert result == "How did you hear about us?"


def test_find_column_no_match_returns_none():
    df = _df_with_cols("Username")
    assert find_column(df, ["NonExistent"]) is None


def test_find_column_empty_df_returns_none():
    assert find_column(pd.DataFrame(), ["Username"]) is None


def test_find_column_none_returns_none():
    assert find_column(None, ["Username"]) is None


def test_find_column_contains_false_does_not_partial_match():
    df = _df_with_cols("How did you hear about us?")
    # Without contains=True, partial name shouldn't match
    result = find_column(df, ["Referral"], contains=False)
    assert result is None
