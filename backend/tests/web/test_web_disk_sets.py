from __future__ import annotations

import re

from app.core.security import hash_password
from app.db.init_db import seed_default_disk_set
from app.db.models import DiskModel, DiskSetModel, UserModel
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


def _create_private_disk_set(
    db_session,
    *,
    owner_id: int,
    name: str,
    slug: str,
) -> DiskSetModel:
    disk_set = DiskSetModel(
        name=name,
        slug=slug,
        owner_id=owner_id,
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        disks=[
            DiskModel(position=1, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            DiskModel(position=2, sequence="BCDEFGHIJKLMNOPQRSTUVWXYZA"),
            DiskModel(position=3, sequence="CDEFGHIJKLMNOPQRSTUVWXYZAB"),
            DiskModel(position=4, sequence="DEFGHIJKLMNOPQRSTUVWXYZABC"),
        ],
    )
    db_session.add(disk_set)
    db_session.commit()
    db_session.refresh(disk_set)
    return disk_set


def _csrf_token_from_html(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match is not None
    return match.group(1)


def test_anonymous_disk_sets_page_shows_public_set(db_session, db_client) -> None:
    seed_default_disk_set(db_session)

    response = db_client.get("/disk-sets")

    assert response.status_code == 200
    assert "Jefferson Standard" in response.text
    assert "Системный" in response.text
    assert "Наборы дисков" in response.text
    assert 'class="disk-page"' in response.text
    assert "Мои наборы" in response.text
    assert "Доступные наборы" in response.text
    assert "Открыть шифр" in response.text
    assert "Войти" in response.text
    assert "У вас пока нет личных наборов" in response.text
    assert "Создайте набор, чтобы сохранить свой порядок дисков." in response.text
    assert 'class="disk-card card"' in response.text
    assert 'class="card-metrics"' in response.text
    assert 'class="card-metric"' in response.text
    assert 'class="mono-inline text-truncate"' not in response.text
    assert 'class="mono-inline"' in response.text
    assert "Кратко" not in response.text
    assert "Что доступно" not in response.text
    assert "access_token" not in response.text
    assert "refresh_token" not in response.text


def test_anonymous_new_disk_set_redirects_to_login(db_client) -> None:
    response = db_client.get("/disk-sets/new", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_logged_in_disk_sets_page_shows_own_and_public_sets(
    db_session, db_client
) -> None:
    user = _create_user(db_session, "owner@example.com")
    seed_default_disk_set(db_session)
    own_disk_set = _create_private_disk_set(
        db_session,
        owner_id=user.id,
        name="Own Private Set",
        slug="own-private-set",
    )
    foreign_disk_set = _create_private_disk_set(
        db_session,
        owner_id=_create_user(db_session, "foreign@example.com").id,
        name="Foreign Private Set",
        slug="foreign-private-set",
    )

    login_page = db_client.get("/login")
    csrf_token = _csrf_token_from_html(login_page.text)
    login_response = db_client.post(
        "/login",
        data={
            "email": user.email,
            "password": "password123",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    assert login_response.status_code == 303

    response = db_client.get("/disk-sets")

    assert response.status_code == 200
    assert "Jefferson Standard" in response.text
    assert "Мои наборы" in response.text
    assert "Доступные наборы" in response.text
    assert 'class="disk-page"' in response.text
    assert own_disk_set.name in response.text
    assert foreign_disk_set.name not in response.text
    assert "Редактировать" in response.text
    assert "Удалить" in response.text
    assert 'class="disk-card card"' in response.text
    assert 'class="card-metrics"' in response.text
    assert 'class="card-metric"' in response.text
    assert 'class="mono-inline text-truncate"' not in response.text
    assert "Кратко" not in response.text
    assert "Что доступно" not in response.text
    assert "access_token" not in response.text
    assert "refresh_token" not in response.text


def test_logged_in_new_disk_set_page_returns_form(db_session, db_client) -> None:
    user = _create_user(db_session, "new-set-owner@example.com")
    login_page = db_client.get("/login")
    csrf_token = _csrf_token_from_html(login_page.text)
    db_client.post(
        "/login",
        data={
            "email": user.email,
            "password": "password123",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    response = db_client.get("/disk-sets/new")

    assert response.status_code == 200
    assert "Новый набор" in response.text
    assert 'name="csrf_token"' in response.text
    assert "access_token" not in response.text
    assert "refresh_token" not in response.text


def test_disk_set_form_has_disk_generator_controls(db_session, db_client) -> None:
    user = _create_user(db_session, "hint-owner@example.com")
    login_page = db_client.get("/login")
    csrf_token = _csrf_token_from_html(login_page.text)
    db_client.post(
        "/login",
        data={
            "email": user.email,
            "password": "password123",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    response = db_client.get("/disk-sets/new")

    assert response.status_code == 200
    assert "data-alphabet-input" in response.text
    assert "data-disks-textarea" in response.text
    assert "data-disk-count-input" in response.text
    assert "data-generate-disks-button" in response.text
    assert "Сгенерировать диски" in response.text
    assert "Заполнит поле валидными перестановками текущего алфавита." in response.text
    assert "Показать пример" in response.text
    assert 'class="example-summary"' in response.text
    assert 'class="example-code"' in response.text


def test_create_disk_set_uses_current_user_owner_and_ignores_owner_field(
    db_session, db_client
) -> None:
    user = _create_user(db_session, "creator@example.com")
    login_page = db_client.get("/login")
    login_csrf = _csrf_token_from_html(login_page.text)
    db_client.post(
        "/login",
        data={
            "email": user.email,
            "password": "password123",
            "csrf_token": login_csrf,
        },
        follow_redirects=False,
    )
    new_page = db_client.get("/disk-sets/new")
    csrf_token = _csrf_token_from_html(new_page.text)

    response = db_client.post(
        "/disk-sets",
        data={
            "name": "Creator Set",
            "slug": "creator-set",
            "alphabet": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "disks": (
                "1:ABCDEFGHIJKLMNOPQRSTUVWXYZ\n"
                "2:BCDEFGHIJKLMNOPQRSTUVWXYZA\n"
                "3:CDEFGHIJKLMNOPQRSTUVWXYZAB\n"
                "4:DEFGHIJKLMNOPQRSTUVWXYZABC"
            ),
            "owner_id": "999",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    db_session.expire_all()
    created = db_session.scalar(
        select(DiskSetModel).where(DiskSetModel.slug == "creator-set")
    )
    assert created is not None
    assert created.owner_id == user.id


def test_create_duplicate_slug_shows_field_error(db_session, db_client) -> None:
    user = _create_user(db_session, "duplicate@example.com")
    _create_private_disk_set(
        db_session,
        owner_id=user.id,
        name="Existing Set",
        slug="duplicate-set",
    )
    login_page = db_client.get("/login")
    login_csrf = _csrf_token_from_html(login_page.text)
    db_client.post(
        "/login",
        data={
            "email": user.email,
            "password": "password123",
            "csrf_token": login_csrf,
        },
        follow_redirects=False,
    )
    new_page = db_client.get("/disk-sets/new")
    csrf_token = _csrf_token_from_html(new_page.text)

    response = db_client.post(
        "/disk-sets",
        data={
            "name": "Duplicate Set",
            "slug": "duplicate-set",
            "alphabet": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "disks": (
                "1:ABCDEFGHIJKLMNOPQRSTUVWXYZ\n"
                "2:BCDEFGHIJKLMNOPQRSTUVWXYZA\n"
                "3:CDEFGHIJKLMNOPQRSTUVWXYZAB\n"
                "4:DEFGHIJKLMNOPQRSTUVWXYZABC"
            ),
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert "Такой слаг уже занят." in response.text
    assert "access_token" not in response.text
    assert "refresh_token" not in response.text


def test_create_malformed_disks_shows_line_hint(db_session, db_client) -> None:
    user = _create_user(db_session, "malformed@example.com")
    login_page = db_client.get("/login")
    login_csrf = _csrf_token_from_html(login_page.text)
    db_client.post(
        "/login",
        data={
            "email": user.email,
            "password": "password123",
            "csrf_token": login_csrf,
        },
        follow_redirects=False,
    )
    new_page = db_client.get("/disk-sets/new")
    csrf_token = _csrf_token_from_html(new_page.text)

    response = db_client.post(
        "/disk-sets",
        data={
            "name": "Malformed Set",
            "slug": "malformed-set",
            "alphabet": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "disks": "1:ABCDEFGHIJKLMNOPQRSTUVWXYZ\nbroken-line",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert "Строка 2: используйте формат номер:последовательность." in response.text
    assert "access_token" not in response.text
    assert "refresh_token" not in response.text


def test_create_disk_set_rejects_disk_sequence_with_spaces(
    db_session, db_client
) -> None:
    user = _create_user(db_session, "spaces@example.com")
    login_page = db_client.get("/login")
    login_csrf = _csrf_token_from_html(login_page.text)
    db_client.post(
        "/login",
        data={
            "email": user.email,
            "password": "password123",
            "csrf_token": login_csrf,
        },
        follow_redirects=False,
    )
    new_page = db_client.get("/disk-sets/new")
    csrf_token = _csrf_token_from_html(new_page.text)

    response = db_client.post(
        "/disk-sets",
        data={
            "name": "Spaces Set",
            "slug": "spaces-set",
            "alphabet": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "disks": "1: ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert (
        "Строка 1: последовательность диска не должна содержать пробелы."
        in response.text
    )


def test_create_disk_set_rejects_non_permutation_disk_sequence(
    db_session, db_client
) -> None:
    user = _create_user(db_session, "length@example.com")
    login_page = db_client.get("/login")
    login_csrf = _csrf_token_from_html(login_page.text)
    db_client.post(
        "/login",
        data={
            "email": user.email,
            "password": "password123",
            "csrf_token": login_csrf,
        },
        follow_redirects=False,
    )
    new_page = db_client.get("/disk-sets/new")
    csrf_token = _csrf_token_from_html(new_page.text)

    response = db_client.post(
        "/disk-sets",
        data={
            "name": "Short Set",
            "slug": "short-set",
            "alphabet": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "disks": "1:ADMMWK",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert "Строка 1: диск должен содержать 26 символов, сейчас 6." in response.text


def test_create_disk_set_rejects_duplicate_letters(db_session, db_client) -> None:
    user = _create_user(db_session, "duplicates@example.com")
    login_page = db_client.get("/login")
    login_csrf = _csrf_token_from_html(login_page.text)
    db_client.post(
        "/login",
        data={
            "email": user.email,
            "password": "password123",
            "csrf_token": login_csrf,
        },
        follow_redirects=False,
    )
    new_page = db_client.get("/disk-sets/new")
    csrf_token = _csrf_token_from_html(new_page.text)

    response = db_client.post(
        "/disk-sets",
        data={
            "name": "Duplicate Letters Set",
            "slug": "duplicate-letters-set",
            "alphabet": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "disks": "1:AAAAAAAAAAAAAAAAAAAAAAAAAA",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert (
        "Строка 1: диск должен содержать все символы алфавита ровно один раз."
        in response.text
    )


def test_edit_own_disk_set_prefills_form(db_session, db_client) -> None:
    user = _create_user(db_session, "edit-owner@example.com")
    disk_set = _create_private_disk_set(
        db_session,
        owner_id=user.id,
        name="Edit Me",
        slug="edit-me",
    )
    login_page = db_client.get("/login")
    csrf_token = _csrf_token_from_html(login_page.text)
    db_client.post(
        "/login",
        data={
            "email": user.email,
            "password": "password123",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    response = db_client.get(f"/disk-sets/{disk_set.id}/edit")

    assert response.status_code == 200
    assert "Редактирование набора" in response.text
    assert "Edit Me" in response.text
    assert "edit-me" in response.text
    assert "access_token" not in response.text
    assert "refresh_token" not in response.text


def test_edit_foreign_or_public_disk_set_returns_404(db_session, db_client) -> None:
    user = _create_user(db_session, "owner-two@example.com")
    login_page = db_client.get("/login")
    csrf_token = _csrf_token_from_html(login_page.text)
    db_client.post(
        "/login",
        data={
            "email": user.email,
            "password": "password123",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    foreign_disk_set = _create_private_disk_set(
        db_session,
        owner_id=_create_user(db_session, "other-owner@example.com").id,
        name="Foreign",
        slug="foreign",
    )
    public_disk_set = seed_default_disk_set(db_session)

    foreign_response = db_client.get(f"/disk-sets/{foreign_disk_set.id}/edit")
    public_response = db_client.get(f"/disk-sets/{public_disk_set.id}/edit")

    assert foreign_response.status_code == 404
    assert public_response.status_code == 404


def test_edit_own_disk_set_updates_fields_and_disks(db_session, db_client) -> None:
    user = _create_user(db_session, "update-owner@example.com")
    disk_set = _create_private_disk_set(
        db_session,
        owner_id=user.id,
        name="Old Name",
        slug="old-slug",
    )
    login_page = db_client.get("/login")
    login_csrf = _csrf_token_from_html(login_page.text)
    db_client.post(
        "/login",
        data={
            "email": user.email,
            "password": "password123",
            "csrf_token": login_csrf,
        },
        follow_redirects=False,
    )
    edit_page = db_client.get(f"/disk-sets/{disk_set.id}/edit")
    csrf_token = _csrf_token_from_html(edit_page.text)

    response = db_client.post(
        f"/disk-sets/{disk_set.id}/edit",
        data={
            "name": "Updated Name",
            "slug": "updated-slug",
            "alphabet": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "disks": (
                "1:ABCDEFGHIJKLMNOPQRSTUVWXYZ\n"
                "2:BCDEFGHIJKLMNOPQRSTUVWXYZA\n"
                "3:CDEFGHIJKLMNOPQRSTUVWXYZAB\n"
                "4:DEFGHIJKLMNOPQRSTUVWXYZABC"
            ),
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    db_session.refresh(disk_set)
    assert disk_set.name == "Updated Name"
    assert disk_set.slug == "updated-slug"
    assert disk_set.owner_id == user.id
    assert len(disk_set.disks) == 4


def test_delete_own_disk_set_removes_it_from_list(db_session, db_client) -> None:
    user = _create_user(db_session, "delete-owner@example.com")
    disk_set = _create_private_disk_set(
        db_session,
        owner_id=user.id,
        name="Delete Me",
        slug="delete-me",
    )
    login_page = db_client.get("/login")
    login_csrf = _csrf_token_from_html(login_page.text)
    db_client.post(
        "/login",
        data={
            "email": user.email,
            "password": "password123",
            "csrf_token": login_csrf,
        },
        follow_redirects=False,
    )
    list_page = db_client.get("/disk-sets")
    csrf_token = _csrf_token_from_html(list_page.text)

    response = db_client.post(
        f"/disk-sets/{disk_set.id}/delete",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )

    assert response.status_code == 303
    disk_set_id = disk_set.id
    db_session.expire_all()
    remaining = db_session.scalar(
        select(DiskSetModel).where(DiskSetModel.id == disk_set_id)
    )
    assert remaining is None


def test_delete_foreign_or_public_disk_set_returns_404(db_session, db_client) -> None:
    user = _create_user(db_session, "delete-owner-two@example.com")
    login_page = db_client.get("/login")
    csrf_token = _csrf_token_from_html(login_page.text)
    db_client.post(
        "/login",
        data={
            "email": user.email,
            "password": "password123",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    foreign_disk_set = _create_private_disk_set(
        db_session,
        owner_id=_create_user(db_session, "foreign-delete@example.com").id,
        name="Foreign Delete",
        slug="foreign-delete",
    )
    public_disk_set = seed_default_disk_set(db_session)

    foreign_response = db_client.post(
        f"/disk-sets/{foreign_disk_set.id}/delete",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )
    public_response = db_client.post(
        f"/disk-sets/{public_disk_set.id}/delete",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )

    assert foreign_response.status_code == 404
    assert public_response.status_code == 404
    foreign_disk_set_id = foreign_disk_set.id
    public_disk_set_id = public_disk_set.id
    db_session.expire_all()
    assert (
        db_session.scalar(
            select(DiskSetModel).where(DiskSetModel.id == foreign_disk_set_id)
        )
        is not None
    )
    assert (
        db_session.scalar(
            select(DiskSetModel).where(DiskSetModel.id == public_disk_set_id)
        )
        is not None
    )
