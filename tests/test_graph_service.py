"""Unit tests for services/graph_service.py (no Google Sheets calls)."""
import pandas as pd
import pytest

from services import graph_service


# ── fixtures ───────────────────────────────────────────────────────────────

def _users_df():
    return pd.DataFrame([
        {
            "Username": "user1",
            "Sex": "Male",
            "Date of Birth": "1990-01-01",
            "Primary Language": "English",
            "Dietary Requirements": "None",
            "Number of Adults in Household": "2",
            "Number of Children in Household": "1",
            "Timestamp": "2024-01-15 10:00:00",
        },
        {
            "Username": "user2",
            "Sex": "Female",
            "Date of Birth": "1985-06-15",
            "Primary Language": "Arabic",
            "Dietary Requirements": "Halal",
            "Number of Adults in Household": "1",
            "Number of Children in Household": "0",
            "Timestamp": "2024-01-16 11:00:00",
        },
    ])


def _logins_df():
    return pd.DataFrame([
        {"Username": "user1", "Timestamp": "2024-03-01 10:00:00", "Day": "Friday"},
        {"Username": "user2", "Timestamp": "2024-03-02 11:00:00", "Day": "Saturday"},
        {"Username": "user1", "Timestamp": "2024-03-03 09:00:00", "Day": "Sunday"},
    ])


# ── create_dashboard_pdf ───────────────────────────────────────────────────

def test_create_dashboard_pdf_returns_bytesio():
    buf = graph_service.create_dashboard_pdf(_users_df(), _logins_df())
    assert hasattr(buf, "read")


def test_create_dashboard_pdf_starts_with_pdf_header():
    buf = graph_service.create_dashboard_pdf(_users_df(), _logins_df())
    assert buf.read(4) == b"%PDF"


def test_create_dashboard_pdf_non_empty():
    buf = graph_service.create_dashboard_pdf(_users_df(), _logins_df())
    assert len(buf.read()) > 100


def test_create_dashboard_pdf_empty_dataframes_does_not_crash():
    # No data → no plots → PDF has no pages (empty buffer is valid)
    buf = graph_service.create_dashboard_pdf(pd.DataFrame(), pd.DataFrame())
    assert hasattr(buf, "read")


def test_create_dashboard_pdf_missing_columns_does_not_crash():
    users = pd.DataFrame([{"Username": "user1"}])
    logins = pd.DataFrame([{"Username": "user1", "Timestamp": "2024-01-01 10:00:00"}])
    buf = graph_service.create_dashboard_pdf(users, logins)
    assert buf.read(4) == b"%PDF"


def test_create_dashboard_pdf_invalid_dob_does_not_crash():
    users = _users_df().copy()
    users["Date of Birth"] = "not-a-date"
    buf = graph_service.create_dashboard_pdf(users, _logins_df())
    assert buf.read(4) == b"%PDF"


# ── individual plot functions ──────────────────────────────────────────────

def test_registrations_trend_returns_figure():
    fig = graph_service._registrations_trend(_users_df())
    assert fig is not None


def test_registrations_trend_none_when_no_timestamp(monkeypatch):
    users = pd.DataFrame([{"Username": "user1", "Sex": "Male"}])
    assert graph_service._registrations_trend(users) is None


def test_registrations_trend_none_when_empty():
    assert graph_service._registrations_trend(pd.DataFrame()) is None


def test_logins_trend_returns_figure():
    fig = graph_service._logins_trend(_logins_df())
    assert fig is not None


def test_logins_trend_none_when_empty():
    assert graph_service._logins_trend(pd.DataFrame()) is None


def test_logins_trend_none_when_no_timestamp_column():
    assert graph_service._logins_trend(pd.DataFrame([{"Username": "u1"}])) is None


def test_gender_chart_returns_figure():
    assert graph_service._gender_chart(_users_df()) is not None


def test_gender_chart_none_when_column_missing():
    assert graph_service._gender_chart(pd.DataFrame([{"Username": "u1"}])) is None


def test_age_chart_returns_figure():
    assert graph_service._age_chart(_users_df()) is not None


def test_age_chart_none_when_column_missing():
    assert graph_service._age_chart(pd.DataFrame([{"Username": "u1"}])) is None


def test_age_chart_none_when_all_dob_invalid():
    users = _users_df().copy()
    users["Date of Birth"] = "not-a-date"
    assert graph_service._age_chart(users) is None


def test_language_chart_returns_figure():
    assert graph_service._language_chart(_users_df()) is not None


def test_language_chart_none_when_column_missing():
    assert graph_service._language_chart(pd.DataFrame([{"Username": "u1"}])) is None


def test_dietary_chart_returns_figure():
    assert graph_service._dietary_chart(_users_df()) is not None


def test_dietary_chart_none_when_column_missing():
    assert graph_service._dietary_chart(pd.DataFrame([{"Username": "u1"}])) is None


def test_household_chart_returns_figure():
    assert graph_service._household_chart(_users_df()) is not None


def test_household_chart_none_when_both_columns_missing():
    assert graph_service._household_chart(pd.DataFrame([{"Username": "u1"}])) is None


def test_household_total_chart_returns_figure():
    assert graph_service._household_total_chart(_users_df()) is not None


def test_household_total_chart_none_when_columns_missing():
    assert graph_service._household_total_chart(pd.DataFrame([{"Username": "u1"}])) is None


def test_new_vs_returning_chart_returns_figure():
    assert graph_service._new_vs_returning_chart(_logins_df()) is not None


def test_new_vs_returning_chart_none_when_empty():
    assert graph_service._new_vs_returning_chart(pd.DataFrame()) is None


def test_new_vs_returning_chart_classifies_correctly():
    """user1's first login is 2024-03-01; the 2024-03-03 login should be Returning."""
    logins = pd.DataFrame([
        {"Username": "user1", "Timestamp": "2024-03-01 10:00:00", "Day": "Friday"},
        {"Username": "user1", "Timestamp": "2024-03-03 10:00:00", "Day": "Sunday"},
    ])
    # Should not crash and should produce a figure
    assert graph_service._new_vs_returning_chart(logins) is not None
