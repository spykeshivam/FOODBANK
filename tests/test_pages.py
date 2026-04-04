def test_home_page_renders_css(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"/static/styles.css" in response.data


def test_login_page_renders_css_and_script(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"/static/styles.css" in response.data
    assert b"loginButton.disabled = true" in response.data
    assert b"Logging in..." in response.data


def test_search_page_renders_css(client):
    response = client.get("/search")
    assert response.status_code == 200
    assert b"/static/styles.css" in response.data


def test_dashboard_page_redirects(client):
    response = client.get("/dashboard")
    assert response.status_code in (301, 302, 308)


def test_dashboard_page_renders_css(client):
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"/static/styles.css" in response.data


