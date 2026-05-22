from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.db.init_db import DEFAULT_DISK_SET_SLUG
from app.db.models import DiskModel, DiskSetModel
from app.db.session import get_session_factory

router = APIRouter(tags=["health"])
BACKEND_ROOT = Path(__file__).resolve().parents[4]
ALEMBIC_INI_PATH = BACKEND_ROOT / "alembic.ini"
EXPECTED_DEFAULT_DISKS = 36


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "jefferson-cipher-service",
        "version": "0.1.0",
    }


def _get_alembic_head_revision() -> str:
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    script = ScriptDirectory.from_config(config)
    head = script.get_current_head()
    if head is None:
        raise RuntimeError("Alembic head revision is not available")
    return head


def _build_ready_payload(
    database: str,
    migrations: str,
    seed: str,
) -> dict[str, str]:
    status = (
        "ready" if (database, migrations, seed) == ("ok", "ok", "ok") else "not_ready"
    )
    return {
        "status": status,
        "database": database,
        "migrations": migrations,
        "seed": seed,
    }


def _ready_response(
    database: str,
    migrations: str,
    seed: str,
) -> JSONResponse:
    payload = _build_ready_payload(database, migrations, seed)
    status_code = 200 if payload["status"] == "ready" else 503
    return JSONResponse(status_code=status_code, content=payload)


@router.get("/ready", response_model=None)
def ready() -> JSONResponse:
    db = None
    try:
        session_factory = get_session_factory()
        db = session_factory()
    except Exception:  # pragma: no cover - defensive boundary for readiness.
        return _ready_response("error", "unknown", "unknown")

    try:
        try:
            db.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return _ready_response("error", "unknown", "unknown")

        try:
            current_revision = db.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()
            head_revision = _get_alembic_head_revision()
        except (SQLAlchemyError, RuntimeError):
            return _ready_response("ok", "error", "unknown")

        if current_revision != head_revision:
            return _ready_response("ok", "error", "unknown")

        try:
            disk_set_id = db.scalar(
                select(DiskSetModel.id).where(
                    DiskSetModel.slug == DEFAULT_DISK_SET_SLUG
                )
            )
            if disk_set_id is None:
                return _ready_response("ok", "ok", "error")

            disks_count = db.scalar(
                select(func.count(DiskModel.id)).where(
                    DiskModel.disk_set_id == disk_set_id
                )
            )
        except SQLAlchemyError:
            return _ready_response("ok", "ok", "error")

        if disks_count != EXPECTED_DEFAULT_DISKS:
            return _ready_response("ok", "ok", "error")

        return _ready_response("ok", "ok", "ok")
    finally:
        if db is not None:
            db.close()
