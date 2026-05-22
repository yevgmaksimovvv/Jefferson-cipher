from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("app.audit")


def log_audit_event(event: str, **fields: Any) -> None:
    """Логирует событие аудита в формате key=value."""
    parts = [f"event={event}"]
    for key, value in fields.items():
        if value is None:
            continue
        parts.append(f"{key}={value}")
    logger.info(" ".join(parts))
