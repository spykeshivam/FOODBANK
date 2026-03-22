from services import data_service


def test_check_user_known(client, monkeypatch):
    monkeypatch.setattr(
        data_service,
        "get_user_details",
        lambda _user_id: {
            "message": "User ID 'abc' exists!",
            "exists": True,
            "details": {"First Name": "A", "Last Name": "B", "Last Login Date": "Today"},
            "show_login_button": True,
        },
    )

    response = client.post("/check_user", data={"user_id": "abc"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["exists"] is True
    assert payload["show_login_button"] is True


def test_check_user_unknown(client, monkeypatch):
    monkeypatch.setattr(
        data_service,
        "get_user_details",
        lambda _user_id: {"message": "User ID 'xyz' does not exist.", "exists": False},
    )

    response = client.post("/check_user", data={"user_id": "xyz"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["exists"] is False


def test_check_user_empty_input(client):
    response = client.post("/check_user", data={"user_id": ""})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["exists"] is False
    assert "No ID provided" in payload["message"]


def test_check_user_trims_whitespace(client, monkeypatch):
    captured = []

    def fake_get_user_details(user_id):
        captured.append(user_id)
        return {"message": "ok", "exists": False}

    monkeypatch.setattr(data_service, "get_user_details", fake_get_user_details)
    client.post("/check_user", data={"user_id": "  abc  "})
    assert captured == ["abc"]


def test_log_login_success(client, monkeypatch):
    monkeypatch.setattr(data_service, "append_login", lambda _user_id: (True, "OK"))
    response = client.post("/log_login", data={"user_id": "abc"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["message"] == "OK"


def test_log_login_trims_whitespace(client, monkeypatch):
    captured = []

    def fake_append_login(user_id):
        captured.append(user_id)
        return True, "OK"

    monkeypatch.setattr(data_service, "append_login", fake_append_login)
    client.post("/log_login", data={"user_id": "  abc  "})
    assert captured == ["abc"]


def test_log_login_no_id(client):
    response = client.post("/log_login", data={"user_id": ""})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is False
    assert "No ID provided" in payload["message"]


def test_check_user_service_failure_returns_safe_error(client, monkeypatch):
    def boom(_user_id):
        raise RuntimeError("Sheets down")

    monkeypatch.setattr(data_service, "get_user_details", boom)
    response = client.post("/check_user", data={"user_id": "abc"})
    assert response.status_code == 500
    payload = response.get_json()
    assert payload["exists"] is False
    assert "Server Error" in payload["message"]


def test_log_login_service_failure_returns_safe_error(client, monkeypatch):
    def boom(_user_id):
        raise RuntimeError("Sheets down")

    monkeypatch.setattr(data_service, "append_login", boom)
    response = client.post("/log_login", data={"user_id": "abc"})
    assert response.status_code == 500
    payload = response.get_json()
    assert payload["success"] is False
    assert "Server Error" in payload["message"]
