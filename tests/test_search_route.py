"""Tests for the /search (GET) and /search_user (POST) routes."""
from services import data_service


def test_search_page_get_returns_200(client):
    response = client.get("/search")
    assert response.status_code == 200


def test_search_page_get_renders_form(client):
    response = client.get("/search")
    assert b"search_type" in response.data or b"Search" in response.data


def test_search_by_name_returns_results(client, monkeypatch):
    monkeypatch.setattr(
        data_service,
        "perform_search",
        lambda search_type, name="", postcode="", dob="": (
            ["John Doe - SW1A 1AA - 1990-01-01 - Username: user1"],
            None,
        ),
    )
    response = client.post("/search_user", data={"search_type": "name", "name": "John"})
    assert response.status_code == 200
    assert b"John Doe" in response.data


def test_search_by_postcode_returns_results(client, monkeypatch):
    monkeypatch.setattr(
        data_service,
        "perform_search",
        lambda search_type, name="", postcode="", dob="": (
            ["John Doe - SW1A 1AA - 1990-01-01 - Username: user1"],
            None,
        ),
    )
    response = client.post("/search_user", data={"search_type": "postcode", "postcode": "SW1A"})
    assert response.status_code == 200
    assert b"John Doe" in response.data


def test_search_by_dob_returns_results(client, monkeypatch):
    monkeypatch.setattr(
        data_service,
        "perform_search",
        lambda search_type, name="", postcode="", dob="": (
            ["John Doe - SW1A 1AA - 1990-01-01 - Username: user1"],
            None,
        ),
    )
    response = client.post("/search_user", data={"search_type": "dob", "dob": "1990-01-01"})
    assert response.status_code == 200
    assert b"John Doe" in response.data


def test_search_no_results_shows_message(client, monkeypatch):
    monkeypatch.setattr(
        data_service,
        "perform_search",
        lambda search_type, name="", postcode="", dob="": ([], "No results found."),
    )
    response = client.post("/search_user", data={"search_type": "name", "name": "ZZZNOMATCH"})
    assert response.status_code == 200
    assert b"No results found" in response.data


def test_search_empty_data_shows_message(client, monkeypatch):
    monkeypatch.setattr(
        data_service,
        "perform_search",
        lambda search_type, name="", postcode="", dob="": ([], "No data available."),
    )
    response = client.post("/search_user", data={"search_type": "name", "name": "John"})
    assert response.status_code == 200
    assert b"No data available" in response.data


def test_search_whitespace_is_stripped(client, monkeypatch):
    captured = {}

    def fake_search(search_type, name="", postcode="", dob=""):
        captured["name"] = name
        return [], "No results found."

    monkeypatch.setattr(data_service, "perform_search", fake_search)
    client.post("/search_user", data={"search_type": "name", "name": "  John  "})
    assert captured["name"] == "John"


def test_search_multiple_results_all_rendered(client, monkeypatch):
    monkeypatch.setattr(
        data_service,
        "perform_search",
        lambda search_type, name="", postcode="", dob="": (
            ["Alice Smith - E1 1AA - 1988-05-10 - Username: u1",
             "John Smith - E2 2BB - 1992-07-22 - Username: u2"],
            None,
        ),
    )
    response = client.post("/search_user", data={"search_type": "name", "name": "Smith"})
    assert response.status_code == 200
    assert b"Alice Smith" in response.data
    assert b"John Smith" in response.data
