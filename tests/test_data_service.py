"""Unit tests for services/data_service.py (all Google Sheets calls mocked)."""
import pandas as pd
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from services import data_service


# ── helpers ────────────────────────────────────────────────────────────────

def _users_df():
    return pd.DataFrame([{
        "Username": "user1",
        "First Name": "John",
        "Surname": "Doe",
        "Date of Birth": "1990-01-01",
        "Postcode": "SW1A 1AA",
        "Number of Adults in Household": "2",
        "Number of Children in Household": "1",
    }])


def _logins_df():
    return pd.DataFrame([{
        "Username": "user1",
        "Timestamp": "2024-01-15 10:30:00",
        "Day": "Monday",
    }])


# ── get_user_details ───────────────────────────────────────────────────────

def test_get_user_details_exists_with_login_history(monkeypatch):
    monkeypatch.setattr(data_service, "get_all_data_frames", lambda: (_users_df(), _logins_df()))
    result = data_service.get_user_details("user1")
    assert result["exists"] is True
    assert result["details"]["First Name"] == "John"
    assert result["details"]["Last Name"] == "Doe"
    assert "2024-01-15" in result["details"]["Last Login Date"]
    assert result["show_login_button"] is True


def test_get_user_details_exists_no_login_history(monkeypatch):
    empty_logins = pd.DataFrame(columns=["Username", "Timestamp", "Day"])
    monkeypatch.setattr(data_service, "get_all_data_frames", lambda: (_users_df(), empty_logins))
    result = data_service.get_user_details("user1")
    assert result["exists"] is True
    assert result["details"]["Last Login Date"] == "No Last Login Date Found"


def test_get_user_details_user_not_found(monkeypatch):
    monkeypatch.setattr(data_service, "get_all_data_frames", lambda: (_users_df(), _logins_df()))
    result = data_service.get_user_details("unknown_id")
    assert result["exists"] is False
    assert "does not exist" in result["message"]


def test_get_user_details_missing_timestamp_column_does_not_crash(monkeypatch):
    """Bug fix: last_entry.get() should handle missing Timestamp/Day columns."""
    logins_no_cols = pd.DataFrame([{"Username": "user1"}])
    monkeypatch.setattr(data_service, "get_all_data_frames", lambda: (_users_df(), logins_no_cols))
    result = data_service.get_user_details("user1")
    assert result["exists"] is True
    # Should not crash; last login date should be a string
    assert isinstance(result["details"]["Last Login Date"], str)


def test_get_user_details_whitespace_username_matched(monkeypatch):
    """Username with surrounding whitespace in sheet should still match."""
    df = _users_df().copy()
    df.loc[0, "Username"] = "  user1  "
    monkeypatch.setattr(data_service, "get_all_data_frames", lambda: (df, _logins_df()))
    result = data_service.get_user_details("user1")
    assert result["exists"] is True


# ── perform_search ─────────────────────────────────────────────────────────

def test_perform_search_by_name_found(monkeypatch):
    monkeypatch.setattr(data_service, "get_all_data_frames", lambda: (_users_df(), _logins_df()))
    results, error = data_service.perform_search("name", name="John")
    assert error is None
    assert len(results) == 1
    assert "John" in results[0]


def test_perform_search_by_name_case_insensitive(monkeypatch):
    monkeypatch.setattr(data_service, "get_all_data_frames", lambda: (_users_df(), _logins_df()))
    results, error = data_service.perform_search("name", name="john")
    assert error is None
    assert len(results) == 1


def test_perform_search_by_surname(monkeypatch):
    monkeypatch.setattr(data_service, "get_all_data_frames", lambda: (_users_df(), _logins_df()))
    results, error = data_service.perform_search("name", name="Doe")
    assert error is None
    assert len(results) == 1


def test_perform_search_by_postcode(monkeypatch):
    monkeypatch.setattr(data_service, "get_all_data_frames", lambda: (_users_df(), _logins_df()))
    results, error = data_service.perform_search("postcode", postcode="SW1A")
    assert error is None
    assert len(results) == 1


def test_perform_search_by_dob(monkeypatch):
    monkeypatch.setattr(data_service, "get_all_data_frames", lambda: (_users_df(), _logins_df()))
    results, error = data_service.perform_search("dob", dob="1990-01-01")
    assert error is None
    assert len(results) == 1


def test_perform_search_no_results(monkeypatch):
    monkeypatch.setattr(data_service, "get_all_data_frames", lambda: (_users_df(), _logins_df()))
    results, error = data_service.perform_search("name", name="ZZZNOMATCH")
    assert results == []
    assert "No results found" in error


def test_perform_search_empty_dataframe(monkeypatch):
    monkeypatch.setattr(data_service, "get_all_data_frames", lambda: (pd.DataFrame(), pd.DataFrame()))
    results, error = data_service.perform_search("name", name="John")
    assert results == []
    assert "No data available" in error


def test_perform_search_invalid_type(monkeypatch):
    monkeypatch.setattr(data_service, "get_all_data_frames", lambda: (_users_df(), _logins_df()))
    results, error = data_service.perform_search("email", name="John")
    assert results == []
    assert "Invalid" in error


def test_perform_search_result_contains_username(monkeypatch):
    monkeypatch.setattr(data_service, "get_all_data_frames", lambda: (_users_df(), _logins_df()))
    results, _ = data_service.perform_search("name", name="John")
    assert "user1" in results[0]



# ── append_login ───────────────────────────────────────────────────────────

def _mock_sheet(records, append_response=None):
    sheet = MagicMock()
    sheet.get_all_records.return_value = records
    sheet.append_row.return_value = append_response or {"updates": {"updatedRange": "Sheet1!A2"}}
    return sheet


def _mock_client(sheet):
    client = MagicMock()
    client.open_by_key.return_value.worksheet.return_value = sheet
    return client


def test_append_login_first_time_user_succeeds(monkeypatch):
    sheet = _mock_sheet([])
    monkeypatch.setattr(data_service, "get_client", lambda: _mock_client(sheet))
    monkeypatch.setattr(data_service, "cache", MagicMock())
    success, message = data_service.append_login("newuser")
    assert success is True
    sheet.append_row.assert_called_once()


def test_append_login_debounce_blocks_within_5_minutes(monkeypatch):
    recent_ts = (datetime.now() - timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
    sheet = _mock_sheet([{"Username": "user1", "Timestamp": recent_ts, "Day": "Monday"}])
    monkeypatch.setattr(data_service, "get_client", lambda: _mock_client(sheet))
    monkeypatch.setattr(data_service, "cache", MagicMock())
    success, message = data_service.append_login("user1")
    assert success is True
    assert "skipped" in message.lower() or "duplicate" in message.lower()
    sheet.append_row.assert_not_called()


def test_append_login_allows_after_5_minutes(monkeypatch):
    old_ts = (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    sheet = _mock_sheet([{"Username": "user1", "Timestamp": old_ts, "Day": "Monday"}])
    monkeypatch.setattr(data_service, "get_client", lambda: _mock_client(sheet))
    monkeypatch.setattr(data_service, "cache", MagicMock())
    success, _ = data_service.append_login("user1")
    assert success is True
    sheet.append_row.assert_called_once()


def test_append_login_google_api_error_returns_false(monkeypatch):
    def boom():
        raise Exception("Network error")
    monkeypatch.setattr(data_service, "get_client", boom)
    success, message = data_service.append_login("user1")
    assert success is False
    assert "Server Error" in message


def test_append_login_clears_cache_on_success(monkeypatch):
    sheet = _mock_sheet([])
    mock_cache = MagicMock()
    monkeypatch.setattr(data_service, "get_client", lambda: _mock_client(sheet))
    monkeypatch.setattr(data_service, "cache", mock_cache)
    data_service.append_login("user1")
    mock_cache.delete.assert_called_once_with("all_data")


def test_append_login_written_row_contains_username(monkeypatch):
    sheet = _mock_sheet([])
    monkeypatch.setattr(data_service, "get_client", lambda: _mock_client(sheet))
    monkeypatch.setattr(data_service, "cache", MagicMock())
    data_service.append_login("user42")
    call_args = sheet.append_row.call_args[0][0]
    assert "user42" in call_args
