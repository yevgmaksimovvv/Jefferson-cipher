from __future__ import annotations

import re

from app.core.security import hash_password
from app.db.models import DiskModel, DiskSetModel, UserModel


def _create_user(db_session, email: str, password: str = "password123") -> UserModel:
    user = UserModel(
        email=email,
        hashed_password=hash_password(password),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _set_cookie_headers(response) -> list[str]:
    headers = response.headers
    if hasattr(headers, "get_list"):
        return headers.get_list("set-cookie")
    value = headers.get("set-cookie")
    return [value] if value else []


def _csrf_token_from_html(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match is not None
    return match.group(1)


def test_login_get_sets_csrf_cookie(db_client) -> None:
    response = db_client.get("/login")

    assert response.status_code == 200
    cookie_headers = _set_cookie_headers(response)
    assert any("web_csrf_token=" in header for header in cookie_headers)
    assert any("samesite=lax" in header.lower() for header in cookie_headers)
    assert 'name="csrf_token"' in response.text


def test_web_base_uses_local_static_assets(db_client) -> None:
    response = db_client.get("/")

    assert response.status_code == 200
    assert 'href="/static/app.css"' in response.text
    assert 'src="/static/app.js"' in response.text
    assert 'src="/static/vendor/htmx-shim.js"' in response.text
    assert 'src="/static/vendor/alpine-shim.js"' in response.text
    assert "http://localhost/static" not in response.text
    assert "https://localhost/static" not in response.text
    assert "https://cdn" not in response.text


def test_web_post_routes_require_csrf(db_session, db_client) -> None:
    user = _create_user(db_session, "csrf@example.com")
    seed_login_page = db_client.get("/login")
    login_csrf = _csrf_token_from_html(seed_login_page.text)
    login_response = db_client.post(
        "/login",
        data={
            "email": user.email,
            "password": "password123",
            "csrf_token": login_csrf,
        },
        follow_redirects=False,
    )
    assert login_response.status_code == 303

    private_disk_set = DiskSetModel(
        name="Private CSRF Set",
        slug="private-csrf-set",
        owner_id=user.id,
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        disks=[
            DiskModel(position=1, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            DiskModel(position=2, sequence="BCDEFGHIJKLMNOPQRSTUVWXYZA"),
            DiskModel(position=3, sequence="CDEFGHIJKLMNOPQRSTUVWXYZAB"),
            DiskModel(position=4, sequence="DEFGHIJKLMNOPQRSTUVWXYZABC"),
        ],
    )
    db_session.add(private_disk_set)
    db_session.commit()

    login_response = db_client.post(
        "/login",
        data={"email": "csrf@example.com", "password": "password123"},
        follow_redirects=False,
    )
    assert login_response.status_code == 403

    register_response = db_client.post(
        "/register",
        data={"email": "new@example.com", "password": "password123"},
        follow_redirects=False,
    )
    assert register_response.status_code == 403

    logout_response = db_client.post("/logout", follow_redirects=False)
    assert logout_response.status_code == 403

    cipher_response = db_client.post(
        "/cipher",
        data={
            "mode": "encrypt",
            "text": "HELLO",
            "disk_set_id": "1",
            "disk_order": "1,2,3,4",
            "offset": "0",
        },
        follow_redirects=False,
    )
    assert cipher_response.status_code == 403

    disk_sets_create_response = db_client.post(
        "/disk-sets",
        data={
            "name": "New Set",
            "slug": "new-set",
            "alphabet": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "disks": "1:ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        },
        follow_redirects=False,
    )
    assert disk_sets_create_response.status_code == 403

    disk_sets_edit_response = db_client.post(
        f"/disk-sets/{private_disk_set.id}/edit",
        data={
            "name": "Private CSRF Set",
            "slug": "private-csrf-set",
            "alphabet": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "disks": "1:ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        },
        follow_redirects=False,
    )
    assert disk_sets_edit_response.status_code == 403

    disk_sets_delete_response = db_client.post(
        f"/disk-sets/{private_disk_set.id}/delete",
        follow_redirects=False,
    )
    assert disk_sets_delete_response.status_code == 403


def test_invalid_csrf_is_rejected(db_session, db_client) -> None:
    _create_user(db_session, "invalid-csrf@example.com")
    login_page = db_client.get("/login")
    valid_csrf = _csrf_token_from_html(login_page.text)

    response = db_client.post(
        "/login",
        data={
            "email": "invalid-csrf@example.com",
            "password": "password123",
            "csrf_token": f"{valid_csrf}-broken",
        },
        follow_redirects=False,
    )

    assert response.status_code == 403
    assert "Неверный CSRF-токен." in response.text


def test_valid_csrf_login_sets_auth_cookies(db_session, db_client) -> None:
    _create_user(db_session, "valid-csrf@example.com")
    login_page = db_client.get("/login")
    csrf_token = _csrf_token_from_html(login_page.text)

    response = db_client.post(
        "/login",
        data={
            "email": "valid-csrf@example.com",
            "password": "password123",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    cookie_headers = _set_cookie_headers(response)
    access_cookie = [
        header for header in cookie_headers if "web_access_token=" in header
    ]
    refresh_cookie = [
        header for header in cookie_headers if "web_refresh_token=" in header
    ]
    csrf_cookie = [header for header in cookie_headers if "web_csrf_token=" in header]
    assert access_cookie and refresh_cookie and csrf_cookie
    assert all("HttpOnly" in header for header in access_cookie + refresh_cookie)
    assert all("HttpOnly" not in header for header in csrf_cookie)


def test_web_html_renders_only_csrf_hidden_input(db_client) -> None:
    for path in ["/login", "/register", "/cipher"]:
        response = db_client.get(path)
        assert response.status_code == 200
        assert 'name="csrf_token"' in response.text
        assert "access_token" not in response.text
        assert "refresh_token" not in response.text

    response = db_client.get("/disk-sets")
    assert response.status_code == 200
    assert "access_token" not in response.text
    assert "refresh_token" not in response.text


def test_api_login_works_without_csrf(db_session, db_client) -> None:
    _create_user(db_session, "api-csrf@example.com")

    response = db_client.post(
        "/api/v1/auth/login",
        json={"email": "api-csrf@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "access_token" in payload
    assert "refresh_token" in payload
