"""Tests for authentication system."""


def test_login_page_returns_200(anon_client):
    r = anon_client.get("/login")
    assert r.status_code == 200
    assert b"Contrase" in r.data


def test_protected_route_redirects_to_login(anon_client):
    r = anon_client.get("/")
    assert r.status_code == 302
    assert "/login" in r.headers.get("Location", "")


def test_login_with_correct_password(anon_client):
    r = anon_client.post("/login", data={"password": "admin123"},
                         follow_redirects=False)
    assert r.status_code == 302
    assert r.headers.get("Location", "").endswith("/")


def test_login_with_wrong_password(anon_client):
    r = anon_client.post("/login", data={"password": "wrong"})
    assert r.status_code == 200
    assert b"incorrecta" in r.data


def test_logout_clears_session(client):
    """Logout redirects to login."""
    r = client.get("/logout", follow_redirects=False)
    assert r.status_code == 302
    assert "/login" in r.headers.get("Location", "")


def test_protected_routes_accessible_with_session(client):
    routes = ["/", "/diario", "/mayor", "/balanza", "/catalogar",
              "/cierre-mensual", "/caja", "/cobrar", "/kardex"]
    for path in routes:
        r = client.get(path)
        assert r.status_code == 200, f"{path} returned {r.status_code}"
