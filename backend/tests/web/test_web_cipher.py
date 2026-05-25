from __future__ import annotations

import re

from app.core.security import hash_password
from app.db.init_db import seed_default_disk_set
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


def _create_compact_public_disk_set(db_session) -> DiskSetModel:
    disk_set = DiskSetModel(
        name="Compact Public Set",
        slug="compact-public-set",
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


def _cipher_payload(
    *,
    disk_set_id: int,
    text: str = "HELLOWORLD",
    disk_order: str = "1,2,3,4",
    offset: str = "2",
    mode: str = "encrypt",
) -> dict[str, str]:
    return {
        "mode": mode,
        "text": text,
        "disk_set_id": str(disk_set_id),
        "disk_order": disk_order,
        "offset": offset,
    }


def _csrf_token_from_html(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match is not None
    return match.group(1)


def test_cipher_page_anonymous_shows_public_disk_set(db_session, db_client) -> None:
    seed_default_disk_set(db_session)

    response = db_client.get("/cipher")

    assert response.status_code == 200
    assert "Jefferson Standard" in response.text
    assert "Системный" in response.text
    assert "Шифрование и расшифровка" in response.text
    assert "Зашифровать" in response.text
    assert "Расшифровать" in response.text
    assert "Здесь появится результат после выполнения операции." in response.text
    assert 'name="explanation_open"' in response.text
    assert "data-explanation-open-input" in response.text
    assert 'class="mobile-nav-panel hidden"' in response.text
    assert 'class="nav-links desktop-only"' in response.text
    assert 'class="mobile-nav-toggle mobile-only btn btn-ghost"' in response.text
    assert 'class="cipher-layout"' in response.text
    assert "<textarea" in response.text
    assert 'name="disk_order"' in response.text
    assert "disk-order-input" in response.text
    assert 'id="offset"' in response.text
    assert 'type="text"' in response.text
    assert 'type="number"' not in response.text
    assert 'inputmode="numeric"' in response.text
    assert 'pattern="-?[0-9]*"' in response.text
    assert 'name="include_' + 'trace"' not in response.text


def test_cipher_page_authenticated_shows_private_disk_set(
    db_session, db_client
) -> None:
    user = _create_user(db_session, "cipher-owner@example.com")
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
    db_session.add(
        DiskSetModel(
            name="Private Set",
            slug="private-set",
            owner_id=user.id,
            alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            disks=[
                DiskModel(position=1, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
                DiskModel(position=2, sequence="BCDEFGHIJKLMNOPQRSTUVWXYZA"),
                DiskModel(position=3, sequence="CDEFGHIJKLMNOPQRSTUVWXYZAB"),
                DiskModel(position=4, sequence="DEFGHIJKLMNOPQRSTUVWXYZABC"),
            ],
        )
    )
    db_session.commit()

    response = db_client.get("/cipher")

    assert response.status_code == 200
    assert "Private Set" in response.text
    assert "Личный" in response.text


def test_cipher_page_prefills_selected_disk_set_from_query_param(
    db_session, db_client
) -> None:
    disk_set = _create_compact_public_disk_set(db_session)

    response = db_client.get(f"/cipher?disk_set_id={disk_set.id}")

    assert response.status_code == 200
    assert f'value="{disk_set.id}" selected' in response.text


def test_cipher_encrypt_and_decrypt_round_trip(db_session, db_client) -> None:
    disk_set = _create_compact_public_disk_set(db_session)
    cipher_page = db_client.get("/cipher")
    csrf_token = _csrf_token_from_html(cipher_page.text)

    encrypt_response = db_client.post(
        "/cipher",
        data={
            **_cipher_payload(disk_set_id=disk_set.id, mode="encrypt"),
            "csrf_token": csrf_token,
        },
    )

    assert encrypt_response.status_code == 200
    assert "JGNNQYQTNF" in encrypt_response.text
    assert "Результат" in encrypt_response.text
    assert "Скопировать" in encrypt_response.text
    assert 'class="card result-card"' in encrypt_response.text
    assert 'id="cipher-output"' in encrypt_response.text
    assert 'data-copy-target="cipher-output"' in encrypt_response.text
    assert "Вывод" not in encrypt_response.text
    assert "Операция шифрования выполнена" not in encrypt_response.text
    assert 'class="alert alert-success"' not in encrypt_response.text
    assert 'id="cipher-workspace"' in encrypt_response.text
    assert 'class="cipher-layout"' in encrypt_response.text
    assert encrypt_response.text.index('class="cipher-layout"') < (
        encrypt_response.text.index('id="cipher-result"')
    )
    assert "access_token" not in encrypt_response.text
    assert "refresh_token" not in encrypt_response.text

    decrypt_response = db_client.post(
        "/cipher",
        data={
            **_cipher_payload(
                disk_set_id=disk_set.id,
                text="JGNNQYQTNF",
                mode="decrypt",
            ),
            "csrf_token": csrf_token,
        },
    )

    assert decrypt_response.status_code == 200
    assert "HELLOWORLD" in decrypt_response.text


def test_cipher_result_card_is_compact(db_session, db_client) -> None:
    disk_set = _create_compact_public_disk_set(db_session)
    cipher_page = db_client.get("/cipher")
    csrf_token = _csrf_token_from_html(cipher_page.text)

    response = db_client.post(
        "/cipher",
        data={
            **_cipher_payload(disk_set_id=disk_set.id),
            "csrf_token": csrf_token,
        },
    )

    assert response.status_code == 200
    assert 'class="card result-card"' in response.text
    assert 'id="cipher-output"' in response.text
    assert 'data-copy-target="cipher-output"' in response.text
    assert "Результат" in response.text
    assert "Скопировать" in response.text
    assert "Операция шифрования выполнена" not in response.text
    assert ">Вывод<" not in response.text
    assert 'card-kicker">Вывод' not in response.text
    assert 'class="alert alert-success"' not in response.text


def test_cipher_explanation_open_state_round_trips(db_session, db_client) -> None:
    disk_set = _create_compact_public_disk_set(db_session)
    cipher_page = db_client.get("/cipher")
    csrf_token = _csrf_token_from_html(cipher_page.text)

    open_response = db_client.post(
        "/cipher",
        data={
            **_cipher_payload(disk_set_id=disk_set.id),
            "explanation_open": "1",
            "csrf_token": csrf_token,
        },
    )
    assert open_response.status_code == 200
    assert (
        '<details class="explanation-details" '
        'data-persist-details="cipher-explanation" open>' in open_response.text
    )

    closed_response = db_client.post(
        "/cipher",
        data={
            **_cipher_payload(disk_set_id=disk_set.id),
            "explanation_open": "0",
            "csrf_token": csrf_token,
        },
    )
    assert closed_response.status_code == 200
    assert (
        '<details class="explanation-details" '
        'data-persist-details="cipher-explanation" open>' not in closed_response.text
    )


def test_cipher_form_carries_explanation_open_hidden_input(
    db_client,
) -> None:
    response = db_client.get("/cipher")

    assert response.status_code == 200
    assert "data-explanation-open-input" in response.text
    assert 'name="explanation_open"' in response.text
    assert 'name="include_' + 'trace"' not in response.text


def test_cipher_disk_order_uses_compact_textarea(db_client) -> None:
    response = db_client.get("/cipher")

    assert response.status_code == 200
    assert "<textarea" in response.text
    assert 'name="disk_order"' in response.text
    assert "disk-order-input" in response.text
    assert 'rows="2"' in response.text
    assert 'type="number"' not in response.text


def test_cipher_invalid_form_shows_error_and_does_not_500(
    db_session, db_client
) -> None:
    disk_set = _create_compact_public_disk_set(db_session)
    cipher_page = db_client.get("/cipher")
    csrf_token = _csrf_token_from_html(cipher_page.text)

    response = db_client.post(
        "/cipher",
        data={
            **_cipher_payload(disk_set_id=disk_set.id, disk_order="abc"),
            "csrf_token": csrf_token,
        },
    )

    assert response.status_code == 200
    assert "Порядок дисков должен содержать только числа." in response.text
    assert 'class="alert alert-error"' in response.text
    assert 'class="alert alert-success"' not in response.text
    assert "access_token" not in response.text
    assert "refresh_token" not in response.text


def test_cipher_explanation_has_persist_marker(db_session, db_client) -> None:
    disk_set = _create_compact_public_disk_set(db_session)
    cipher_page = db_client.get("/cipher")
    csrf_token = _csrf_token_from_html(cipher_page.text)

    response = db_client.post(
        "/cipher",
        data={
            **_cipher_payload(disk_set_id=disk_set.id),
            "csrf_token": csrf_token,
        },
    )

    assert response.status_code == 200
    assert 'data-persist-details="cipher-explanation"' in response.text
    assert '<details class="explanation-details" open>' not in response.text


def test_cipher_result_shows_explanation_and_disk_alphabets(
    db_session, db_client
) -> None:
    disk_set = _create_compact_public_disk_set(db_session)
    cipher_page = db_client.get("/cipher")
    csrf_token = _csrf_token_from_html(cipher_page.text)

    response = db_client.post(
        "/cipher",
        data={
            **_cipher_payload(disk_set_id=disk_set.id),
            "csrf_token": csrf_token,
        },
    )

    assert response.status_code == 200
    assert 'id="cipher-workspace"' in response.text
    assert 'data-persist-details="cipher-explanation"' in response.text
    assert '<details class="explanation-details" open>' not in response.text
    assert "Объяснение работы" in response.text
    assert (
        "Порядок дисков, использованные диски и преобразование символов"
        in response.text
    )
    assert "Порядок дисков" in response.text
    assert "Использованные диски" in response.text
    assert "Преобразование символов" in response.text
    assert "Развернуть" in response.text
    assert "Свернуть" in response.text
    assert "Диск №1" in response.text
    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ" in response.text
    assert "Режим" not in response.text
    assert 'class="explanation-step-card"' in response.text
    assert 'class="step-input"' in response.text
    assert 'class="step-output"' in response.text
    assert 'data-copy-target="cipher-output"' in response.text
    assert 'name="include_' + 'trace"' not in response.text
    assert "Нормализованный текст" not in response.text
    assert "Трассировка" not in response.text
    assert "Рассчитать трассировку" not in response.text
    assert "<table" not in response.text
    assert "<th>№</th>" not in response.text
    assert "explanation-steps-table" not in response.text


def test_cipher_result_shows_only_used_disks_for_short_text(
    db_session, db_client
) -> None:
    disk_set = seed_default_disk_set(db_session)
    cipher_page = db_client.get("/cipher")
    csrf_token = _csrf_token_from_html(cipher_page.text)

    response = db_client.post(
        "/cipher",
        data={
            **_cipher_payload(
                disk_set_id=disk_set.id,
                text="H",
                disk_order="1,2,3,4",
            ),
            "csrf_token": csrf_token,
        },
    )

    assert response.status_code == 200
    assert response.text.count('class="explanation-disk-chip"') == 1
    assert "Диск №1" in response.text
    assert "Диск №2" not in response.text
    assert "Диск №36" not in response.text


def test_cipher_result_page_does_not_render_tokens(db_session, db_client) -> None:
    disk_set = _create_compact_public_disk_set(db_session)
    cipher_page = db_client.get("/cipher")
    csrf_token = _csrf_token_from_html(cipher_page.text)

    response = db_client.post(
        "/cipher",
        data={
            **_cipher_payload(disk_set_id=disk_set.id),
            "csrf_token": csrf_token,
        },
    )

    assert response.status_code == 200
    assert "access_token" not in response.text
    assert "refresh_token" not in response.text
