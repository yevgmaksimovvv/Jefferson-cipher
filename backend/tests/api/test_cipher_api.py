def _cipher_payload(*, include_trace: bool = True) -> dict:
    return {
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
