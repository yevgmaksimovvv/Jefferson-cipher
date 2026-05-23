from __future__ import annotations

import ipaddress
import logging
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any

from fastapi import Request

from app.core.config import get_settings, resolve_rate_limit_storage

logger = logging.getLogger(__name__)
WINDOW_SECONDS = 60
_REDIS_RATE_LIMIT_SCRIPT = """
local current = redis.call("INCR", KEYS[1])
if current == 1 then
  redis.call("EXPIRE", KEYS[1], ARGV[1])
end
local ttl = redis.call("TTL", KEYS[1])
return {current, ttl}
"""


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after: int | None = None


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int | None = None) -> None:
        self.retry_after = retry_after
        super().__init__("Rate limit exceeded")


class RateLimiterUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("Rate limiter unavailable")


def _current_window(now: float | None = None) -> int:
    current_time = time.time() if now is None else now
    return int(current_time // WINDOW_SECONDS)


def _retry_after_seconds(now: float | None = None) -> int:
    current_time = time.time() if now is None else now
    return max(1, WINDOW_SECONDS - int(current_time % WINDOW_SECONDS))


def _build_rate_limit_key(bucket: str, client_id: str, now: float | None = None) -> str:
    return f"rate_limit:{bucket}:{client_id}:{_current_window(now)}"


def _safe_client_host(request: Request) -> str:
    client = request.client
    if client is None or not client.host:
        return "unknown"
    return client.host


def _is_trusted_proxy_host(host: str, trusted_proxy_ips: str) -> bool:
    trusted_value = trusted_proxy_ips.strip()
    if not host or not trusted_value:
        return False
    if trusted_value == "*":
        return True
    trusted_hosts = {
        candidate.strip() for candidate in trusted_value.split(",") if candidate.strip()
    }
    return host in trusted_hosts


def _first_valid_forwarded_ip(value: str) -> str | None:
    for candidate in value.split(","):
        candidate = candidate.strip()
        if not candidate:
            continue
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            continue
    return None


def get_client_identifier(request: Request, settings_or_config: Any) -> str:
    client_host = _safe_client_host(request)
    if not getattr(settings_or_config, "TRUST_PROXY_HEADERS", False):
        return client_host
    if not _is_trusted_proxy_host(
        client_host,
        getattr(settings_or_config, "TRUSTED_PROXY_IPS", ""),
    ):
        return client_host
    forwarded_for = request.headers.get("x-forwarded-for")
    if not forwarded_for:
        return client_host
    return _first_valid_forwarded_ip(forwarded_for) or client_host


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._lock = Lock()
        self._hits: dict[str, tuple[int, float]] = {}

    def allow(
        self,
        *,
        bucket: str,
        client_id: str,
        limit: int,
    ) -> RateLimitResult:
        now = time.time()
        key = _build_rate_limit_key(bucket, client_id, now)
        retry_after = _retry_after_seconds(now)
        expires_at = now + retry_after
        with self._lock:
            count, stored_expires_at = self._hits.get(key, (0, expires_at))
            if now >= stored_expires_at:
                count = 0
                stored_expires_at = expires_at
            count += 1
            self._hits[key] = (count, stored_expires_at)
            if count > limit:
                return RateLimitResult(
                    allowed=False,
                    retry_after=max(1, int(stored_expires_at - now)),
                )
            return RateLimitResult(allowed=True)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def status(self) -> str:
        return "memory"


class _UnavailableRateLimiter:
    def allow(
        self,
        *,
        bucket: str,
        client_id: str,
        limit: int,
    ) -> RateLimitResult:
        raise RateLimiterUnavailable()

    def status(self) -> str:
        return "error"


class RedisRateLimiter:
    def __init__(
        self,
        *,
        redis_url: str,
        fail_open: bool = False,
        client: Any | None = None,
    ) -> None:
        self._redis_url = redis_url
        self._fail_open = fail_open
        self._client = client
        self._client_lock = Lock()

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        with self._client_lock:
            if self._client is None:
                self._client = _create_redis_client(self._redis_url)
        return self._client

    def _increment(self, key: str, ttl_seconds: int) -> tuple[int, int]:
        client = self._get_client()
        result = client.eval(_REDIS_RATE_LIMIT_SCRIPT, 1, key, ttl_seconds)
        current = int(result[0])
        ttl = (
            int(result[1]) if len(result) > 1 and result[1] is not None else ttl_seconds
        )
        return current, ttl

    def allow(
        self,
        *,
        bucket: str,
        client_id: str,
        limit: int,
    ) -> RateLimitResult:
        now = time.time()
        key = _build_rate_limit_key(bucket, client_id, now)
        ttl_seconds = _retry_after_seconds(now)
        try:
            current, ttl = self._increment(key, ttl_seconds)
        except RateLimiterUnavailable:
            if self._fail_open:
                return RateLimitResult(allowed=True)
            raise
        except Exception as exc:
            if _is_redis_error(exc):
                if self._fail_open:
                    logger.warning("Rate limiter unavailable, allowing request")
                    return RateLimitResult(allowed=True)
                logger.warning("Rate limiter unavailable")
                raise RateLimiterUnavailable() from exc
            raise

        if ttl <= 0:
            ttl = ttl_seconds
        if current > limit:
            return RateLimitResult(allowed=False, retry_after=max(1, ttl))
        return RateLimitResult(allowed=True)

    def status(self) -> str:
        client = self._get_client()
        ping = getattr(client, "ping", None)
        if not callable(ping):
            raise RateLimiterUnavailable()
        if not ping():
            raise RateLimiterUnavailable()
        return "ok"


def _create_redis_client(redis_url: str) -> Any:
    if not redis_url:
        raise RateLimiterUnavailable()
    try:
        import redis
    except ImportError as exc:
        raise RateLimiterUnavailable() from exc
    return redis.Redis.from_url(redis_url, decode_responses=True)


def _is_redis_error(exc: Exception) -> bool:
    try:
        import redis
    except ImportError:
        return False
    return isinstance(exc, redis.exceptions.RedisError)


_memory_rate_limiter = InMemoryRateLimiter()
_rate_limiter_cache: dict[tuple[str, str | None, bool], RedisRateLimiter] = {}


def reset_rate_limit_state() -> None:
    _memory_rate_limiter.reset()
    _rate_limiter_cache.clear()


def get_rate_limiter(
    settings: Any,
) -> InMemoryRateLimiter | RedisRateLimiter | _UnavailableRateLimiter:
    storage = resolve_rate_limit_storage(
        getattr(settings, "RATE_LIMIT_STORAGE", "auto"),
        getattr(settings, "REDIS_URL", None),
    )
    redis_url = getattr(settings, "REDIS_URL", None)
    fail_open = getattr(settings, "RATE_LIMIT_FAIL_OPEN", False)

    if storage == "memory":
        return _memory_rate_limiter
    if storage == "redis":
        if not redis_url:
            return _UnavailableRateLimiter()
        cache_key = ("redis", redis_url, fail_open)
        limiter = _rate_limiter_cache.get(cache_key)
        if limiter is None:
            limiter = RedisRateLimiter(redis_url=redis_url, fail_open=fail_open)
            _rate_limiter_cache[cache_key] = limiter
        return limiter

    if redis_url:
        cache_key = ("redis", redis_url, fail_open)
        limiter = _rate_limiter_cache.get(cache_key)
        if limiter is None:
            limiter = RedisRateLimiter(redis_url=redis_url, fail_open=fail_open)
            _rate_limiter_cache[cache_key] = limiter
        return limiter
    return _memory_rate_limiter


def get_rate_limiter_status(settings: Any) -> str:
    limiter = get_rate_limiter(settings)
    try:
        return limiter.status()
    except RateLimiterUnavailable:
        return "error"
    except Exception:
        return "error"


def rate_limit(bucket: str, settings_key: str):
    async def dependency(request: Request) -> None:
        settings = get_settings()
        limit = getattr(settings, settings_key)
        limiter = get_rate_limiter(settings)
        result = limiter.allow(
            bucket=bucket,
            client_id=get_client_identifier(request, settings),
            limit=limit,
        )
        if not result.allowed:
            raise RateLimitExceeded(result.retry_after)

    return dependency
