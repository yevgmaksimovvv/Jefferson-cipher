from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic

from fastapi import Request

from app.core.config import get_settings

logger = logging.getLogger(__name__)
WINDOW_SECONDS = 60


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after: int | None = None


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int | None = None) -> None:
        self.retry_after = retry_after
        super().__init__("Rate limit exceeded")


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._lock = Lock()
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, *, key: str, limit: int) -> RateLimitResult:
        now = monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= WINDOW_SECONDS:
                hits.popleft()

            if len(hits) >= limit:
                retry_after = max(1, int(WINDOW_SECONDS - (now - hits[0])))
                return RateLimitResult(allowed=False, retry_after=retry_after)

            hits.append(now)
            return RateLimitResult(allowed=True)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


rate_limiter = InMemoryRateLimiter()


def reset_rate_limit_state() -> None:
    rate_limiter.reset()


def _get_client_host(request: Request) -> str:
    client = request.client
    if client is None or not client.host:
        return "unknown"
    return client.host


def rate_limit(bucket: str, settings_key: str):
    async def dependency(request: Request) -> None:
        settings = get_settings()
        limit = getattr(settings, settings_key)
        result = rate_limiter.allow(
            key=f"{_get_client_host(request)}:{bucket}",
            limit=limit,
        )
        if not result.allowed:
            raise RateLimitExceeded(result.retry_after)

    return dependency
