from __future__ import annotations

import importlib

from fastapi.testclient import TestClient


def test_cipher_api_works_without_database_env(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ALEMBIC_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL_LOCAL", raising=False)

    from app.core.config import get_settings

    get_settings.cache_clear()

    app_main = importlib.import_module("app.main")
    app_main = importlib.reload(app_main)

    client = TestClient(app_main.app)
    response = client.post(
        "/api/v1/cipher/encrypt",
        json={
            "text": "Hello, World! 123",
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
