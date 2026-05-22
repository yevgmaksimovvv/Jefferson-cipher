from app.db.init_db import seed_default_disk_set


def test_list_disk_sets_returns_seeded_default(db_session, db_client) -> None:
    seed_default_disk_set(db_session)

    response = db_client.get("/api/v1/disk-sets")

    assert response.status_code == 200

    body = response.json()
    assert len(body) == 1
    assert body[0]["slug"] == "jefferson-standard"
    assert body[0]["disks_count"] == 36


def test_get_disk_set_returns_full_disks_ordered_by_position(
    db_session, db_client
) -> None:
    disk_set = seed_default_disk_set(db_session)

    response = db_client.get(f"/api/v1/disk-sets/{disk_set.id}")

    assert response.status_code == 200

    body = response.json()
    assert len(body["disks"]) == 36
    assert [disk["position"] for disk in body["disks"]] == list(range(1, 37))


def test_get_disk_set_returns_404_for_missing_id(db_client) -> None:
    response = db_client.get("/api/v1/disk-sets/999999")

    assert response.status_code == 404

    body = response.json()
    assert body["error"]["code"] == "DISK_SET_NOT_FOUND"
    assert "detail" not in body
