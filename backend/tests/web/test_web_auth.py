from __future__ import annotations

import re

from app.core.security import hash_password
from app.db.models import UserModel
from sqlalchemy import select


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


def test_web_home_login_register_render(db_client) -> None:
    assert db_client.get("/").status_code == 200
    assert db_client.get("/login").status_code == 200
    assert db_client.get("/register").status_code == 200


def test_web_register_creates_user_and_sets_http_only_cookies(
    db_session, db_client
) -> None:
    register_page = db_client.get("/register")
    csrf_token = _csrf_token_from_html(register_page.text)

    response = db_client.post(
        "/register",
        data={
            "email": "  New.User@Example.com  ",
            "password": "password123",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"

    cookie_headers = _set_cookie_headers(response)
    access_cookie = [
        header for header in cookie_headers if "web_access_token=" in header
    ]
    refresh_cookie = [
        header for header in cookie_headers if "web_refresh_token=" in header
    ]
    assert access_cookie and refresh_cookie
    assert all("HttpOnly" in header for header in access_cookie + refresh_cookie)

    user = db_session.scalar(
        select(UserModel).where(UserModel.email == "new.user@example.com")
    )
    assert user is not None


def test_web_login_sets_http_only_cookies(db_session, db_client) -> None:
    _create_user(db_session, "login@example.com")
    login_page = db_client.get("/login")
    csrf_token = _csrf_token_from_html(login_page.text)

    response = db_client.post(
        "/login",
        data={
            "email": "login@example.com",
            "password": "password123",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    cookie_headers = _set_cookie_headers(response)
    assert any("web_access_token=" in header for header in cookie_headers)
    assert any("web_refresh_token=" in header for header in cookie_headers)
    assert any("HttpOnly" in header for header in cookie_headers)


def test_web_logout_clears_cookies(db_session, db_client) -> None:
    _create_user(db_session, "logout@example.com")
    login_page = db_client.get("/login")
    csrf_token = _csrf_token_from_html(login_page.text)
    db_client.post(
        "/login",
        data={
            "email": "logout@example.com",
            "password": "password123",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    response = db_client.post(
        "/logout",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )

    assert response.status_code == 303
    cookie_headers = _set_cookie_headers(response)
    assert any("web_access_token=" in header for header in cookie_headers)
    assert any("web_refresh_token=" in header for header in cookie_headers)
    assert any(
        "Max-Age=0" in header or "expires=" in header.lower()
        for header in cookie_headers
    )


def test_html_never_renders_tokens(db_client) -> None:
    for path in ["/", "/login", "/register", "/cipher"]:
        response = db_client.get(path)
        assert response.status_code == 200
        assert "access_token" not in response.text
        assert "refresh_token" not in response.text


def test_invalid_login_shows_error_and_does_not_500(db_session, db_client) -> None:
    _create_user(db_session, "invalid-login@example.com")
    login_page = db_client.get("/login")
    csrf_token = _csrf_token_from_html(login_page.text)

    response = db_client.post(
        "/login",
        data={
            "email": "invalid-login@example.com",
            "password": "bad-password",
            "csrf_token": csrf_token,
        },
    )

    assert response.status_code == 200
    assert "Invalid email or password." in response.text
    assert "access_token" not in response.text
    assert "refresh_token" not in response.text
