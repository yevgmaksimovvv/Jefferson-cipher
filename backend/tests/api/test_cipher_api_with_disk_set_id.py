from app.db.models import DiskModel, DiskSetModel


def _create_compact_disk_set(db_session) -> DiskSetModel:
    disk_set = DiskSetModel(
        name="Test Set",
        slug="test-set",
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
    text: str = "HELLOWORLD",
    include_trace: bool = True,
    disk_set_id: int,
    offset: int = 2,
    disk_order: list[int] | None = None,
) -> dict:
    return {
        "text": text,
        "disk_set_id": disk_set_id,
        "key": {
            "disk_order": disk_order if disk_order is not None else [1, 2, 3, 4],
            "offset": offset,
        },
        "include_trace": include_trace,
    }


def test_encrypt_from_disk_set_returns_expected_result(db_session, db_client) -> None:
    disk_set = _create_compact_disk_set(db_session)

    response = db_client.post(
        "/api/v1/cipher/encrypt/from-disk-set",
        json=_cipher_payload(disk_set_id=disk_set.id),
    )

    assert response.status_code == 200

    body = response.json()
    assert body["text"] == "JGNNQYQTNF"
    assert body["normalized_text"] == "HELLOWORLD"
    assert body["trace"][0]["mode"] == "encrypt"


def test_decrypt_from_disk_set_reverses_encrypt(db_session, db_client) -> None:
    disk_set = _create_compact_disk_set(db_session)
    encrypt_response = db_client.post(
        "/api/v1/cipher/encrypt/from-disk-set",
        json=_cipher_payload(disk_set_id=disk_set.id),
    )
    ciphertext = encrypt_response.json()["text"]

    response = db_client.post(
        "/api/v1/cipher/decrypt/from-disk-set",
        json=_cipher_payload(text=ciphertext, disk_set_id=disk_set.id),
    )

    assert response.status_code == 200

    body = response.json()
    assert body["text"] == "HELLOWORLD"
    assert body["trace"][0]["mode"] == "decrypt"


def test_from_disk_set_can_omit_trace(db_session, db_client) -> None:
    disk_set = _create_compact_disk_set(db_session)

    response = db_client.post(
        "/api/v1/cipher/encrypt/from-disk-set",
        json=_cipher_payload(disk_set_id=disk_set.id, include_trace=False),
    )

    assert response.status_code == 200
    assert response.json()["trace"] == []


def test_from_disk_set_returns_404_for_missing_disk_set(db_client) -> None:
    response = db_client.post(
        "/api/v1/cipher/encrypt/from-disk-set",
        json=_cipher_payload(disk_set_id=999999),
    )

    assert response.status_code == 404

    body = response.json()
    assert body["error"]["code"] == "DISK_SET_NOT_FOUND"
    assert "detail" not in body


def test_from_disk_set_returns_400_for_invalid_key_missing_disk_id(
    db_session, db_client
) -> None:
    disk_set = _create_compact_disk_set(db_session)

    response = db_client.post(
        "/api/v1/cipher/encrypt/from-disk-set",
        json=_cipher_payload(
            disk_set_id=disk_set.id,
            disk_order=[1, 2, 3, 99],
        ),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MissingDiskNumberError"


def test_existing_stateless_cipher_api_still_works(client) -> None:
    response = client.post(
        "/api/v1/cipher/encrypt",
        json={
            "text": "HELLOWORLD",
            "disk_set": {
                "alphabet": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                "disks": [
                    {"id": 1, "sequence": "ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
                    {"id": 2, "sequence": "BCDEFGHIJKLMNOPQRSTUVWXYZA"},
                    {"id": 3, "sequence": "CDEFGHIJKLMNOPQRSTUVWXYZAB"},
                    {"id": 4, "sequence": "DEFGHIJKLMNOPQRSTUVWXYZABC"},
                ],
            },
            "key": {
                "disk_order": [1, 2, 3, 4],
                "offset": 2,
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["text"] == "JGNNQYQTNF"
