def _cipher_payload(
    *,
    text: str = "HELLOWORLD",
    include_trace: bool = True,
    offset: int = 2,
    disk_order: list[int] | None = None,
    disks: list[dict[str, object]] | None = None,
) -> dict:
    return {
        "text": text,
        "disk_set": {
            "alphabet": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "disks": disks
            if disks is not None
            else [
                {"id": 1, "sequence": "ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
                {"id": 2, "sequence": "BCDEFGHIJKLMNOPQRSTUVWXYZA"},
                {"id": 3, "sequence": "CDEFGHIJKLMNOPQRSTUVWXYZAB"},
                {"id": 4, "sequence": "DEFGHIJKLMNOPQRSTUVWXYZABC"},
            ],
        },
        "key": {
            "disk_order": disk_order if disk_order is not None else [1, 2, 3, 4],
            "offset": offset,
        },
        "include_trace": include_trace,
    }


def test_encrypt_endpoint_returns_expected_text(client) -> None:
    response = client.post("/api/v1/cipher/encrypt", json=_cipher_payload())

    assert response.status_code == 200

    body = response.json()
    assert body["text"] == "JGNNQYQTNF"
    assert body["normalized_text"] == "HELLOWORLD"
    assert body["trace"]
    assert body["trace"][0]["mode"] == "encrypt"
    assert body["trace"][0]["disk_id"] == 1
    assert body["trace"][0]["input_char"] == "H"
    assert body["trace"][0]["output_char"] == "J"
    assert body["trace"][0]["input_position"] == 7
    assert body["trace"][0]["output_position"] == 9
    assert body["trace"][0]["offset"] == 2


def test_decrypt_endpoint_reverses_encrypt(client) -> None:
    encrypt_response = client.post("/api/v1/cipher/encrypt", json=_cipher_payload())
    ciphertext = encrypt_response.json()["text"]

    payload = _cipher_payload()
    payload["text"] = ciphertext
    response = client.post("/api/v1/cipher/decrypt", json=payload)

    assert response.status_code == 200

    body = response.json()
    assert body["text"] == "HELLOWORLD"
    assert body["trace"][0]["mode"] == "decrypt"


def test_encrypt_endpoint_normalizes_text_before_encryption(client) -> None:
    payload = _cipher_payload(text="Hello, World! 123")
    response = client.post("/api/v1/cipher/encrypt", json=payload)

    assert response.status_code == 200

    body = response.json()
    assert body["normalized_text"] == "HELLOWORLD"
    assert body["text"] == "JGNNQYQTNF"


def test_decrypt_endpoint_normalizes_ciphertext_before_decryption(client) -> None:
    encrypt_response = client.post("/api/v1/cipher/encrypt", json=_cipher_payload())
    ciphertext = encrypt_response.json()["text"]

    payload = _cipher_payload(
        text=f" {ciphertext[:4].lower()}, {ciphertext[4:].lower()} !"
    )
    response = client.post("/api/v1/cipher/decrypt", json=payload)

    assert response.status_code == 200

    body = response.json()
    assert body["normalized_text"] == ciphertext
    assert body["text"] == "HELLOWORLD"


def test_encrypt_endpoint_offset_zero_keeps_normalized_text(client) -> None:
    payload = _cipher_payload(offset=0)
    response = client.post("/api/v1/cipher/encrypt", json=payload)

    assert response.status_code == 200

    body = response.json()
    assert body["text"] == body["normalized_text"] == "HELLOWORLD"


def test_encrypt_endpoint_offset_26_matches_identity_behavior(client) -> None:
    payload = _cipher_payload(offset=26)
    response = client.post("/api/v1/cipher/encrypt", json=payload)

    assert response.status_code == 200

    body = response.json()
    assert body["text"] == body["normalized_text"] == "HELLOWORLD"


def test_encrypt_endpoint_handles_negative_offset(client) -> None:
    payload = _cipher_payload(offset=-1)
    response = client.post("/api/v1/cipher/encrypt", json=payload)

    assert response.status_code == 200

    body = response.json()
    assert body["text"] == "GDKKNVNQKC"


def test_encrypt_endpoint_normalizes_huge_offset(client) -> None:
    payload = _cipher_payload(offset=(26 * 1000) + 2)
    response = client.post("/api/v1/cipher/encrypt", json=payload)

    assert response.status_code == 200

    body = response.json()
    assert body["text"] == "JGNNQYQTNF"


def test_encrypt_endpoint_returns_400_for_missing_disk_id(client) -> None:
    payload = _cipher_payload()
    payload["key"]["disk_order"] = [1, 2, 3, 99]
    response = client.post("/api/v1/cipher/encrypt", json=payload)

    assert response.status_code == 400

    body = response.json()
    assert body["error"]["code"] == "MissingDiskNumberError"


def test_encrypt_endpoint_returns_400_for_duplicate_disk_order(client) -> None:
    payload = _cipher_payload()
    payload["key"]["disk_order"] = [1, 2, 2, 4]
    response = client.post("/api/v1/cipher/encrypt", json=payload)

    assert response.status_code == 400

    body = response.json()
    assert body["error"]["code"] == "DuplicateDiskNumberError"


def test_encrypt_endpoint_returns_400_for_empty_text_after_normalization(
    client,
) -> None:
    payload = _cipher_payload(text="123 !!!")
    response = client.post("/api/v1/cipher/encrypt", json=payload)

    assert response.status_code == 400

    body = response.json()
    assert body["error"]["code"] == "EmptyTextError"


def test_encrypt_endpoint_includes_trace_by_default(client) -> None:
    payload = _cipher_payload()
    payload.pop("include_trace")
    response = client.post("/api/v1/cipher/encrypt", json=payload)

    assert response.status_code == 200

    body = response.json()
    assert body["trace"]


def test_encrypt_endpoint_accepts_extra_fields_with_current_schema_behavior(
    client,
) -> None:
    payload = _cipher_payload()
    payload["unexpected"] = {"nested": "value"}
    response = client.post("/api/v1/cipher/encrypt", json=payload)

    assert response.status_code == 200

    body = response.json()
    assert body["text"] == "JGNNQYQTNF"


def test_encrypt_endpoint_can_omit_trace(client) -> None:
    payload = _cipher_payload(include_trace=False)
    response = client.post("/api/v1/cipher/encrypt", json=payload)

    assert response.status_code == 200

    body = response.json()
    assert body["text"] == "JGNNQYQTNF"
    assert body["trace"] == []


def test_encrypt_endpoint_returns_400_for_invalid_disk(client) -> None:
    payload = _cipher_payload()
    payload["disk_set"]["disks"][0]["sequence"] = "ABCDEFGHIJKLMNOPQRSTUVWXYA"

    response = client.post("/api/v1/cipher/encrypt", json=payload)

    assert response.status_code == 400

    body = response.json()
    assert "detail" not in body
    assert body["error"]["code"] == "InvalidDiskPermutationError"
    assert body["error"]["message"]


def test_encrypt_endpoint_returns_422_for_invalid_request_shape(client) -> None:
    payload = _cipher_payload()
    payload.pop("text")

    response = client.post("/api/v1/cipher/encrypt", json=payload)

    assert response.status_code == 422
