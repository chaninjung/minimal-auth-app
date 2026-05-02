"""Per-IP rate limiting for the auth endpoints.

A small in-memory sliding-window limiter, wired into FastAPI as a
``Depends`` dependency. We deliberately avoid third-party libraries
(slowapi, etc.) at this scale — the implementation is short enough to
read in a glance, has zero hidden behaviour, and integrates cleanly
with FastAPI's dependency-injection model.

Limits applied:

* ``POST /api/auth/signin`` — 10 requests / minute / IP
* ``POST /api/auth/signup`` — 5 requests / minute / IP

These are intentionally low because both endpoints are authentication
hot paths and we don't expect a single human user to legitimately
exceed them. They pair with the constant-time sign-in path
(REPORT §6) and account-level lockout (REPORT §3 / §6 — planned) for
defence in depth.

Production note: the backing store is a process-local ``dict``. Across
multiple uvicorn workers / pods, each replica has its own counters, so
an attacker effectively gets ``N × limit`` requests. For a real fleet,
swap the storage for Redis (atomic ``INCR`` + ``EXPIRE``) without
changing the public API of this module.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import HTTPException, Request, status

from app.config import Settings, get_settings
from fastapi import Depends


class _SlidingWindow:
    """Thread-safe per-key sliding-window counter."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str) -> bool:
        """Record one request for ``key``. Return True if allowed, False if over the limit."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            bucket = self._buckets[key]
            # Drop timestamps older than the window.
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                return False
            bucket.append(now)
            return True


# Module-level limiters — shared across requests within a process.
_signin_limiter = _SlidingWindow(max_requests=10, window_seconds=60)
_signup_limiter = _SlidingWindow(max_requests=5, window_seconds=60)


def _client_ip(request: Request) -> str:
    """Best-effort client IP. Behind a proxy/CDN, the LB should set
    ``X-Forwarded-For`` and the ASGI server should be configured to
    trust it; ``request.client.host`` then reflects the real IP."""
    if request.client is None:
        return "unknown"
    return request.client.host


def _enforce(limiter: _SlidingWindow, request: Request, settings: Settings) -> None:
    if not settings.rate_limit_enabled:
        return
    if not limiter.hit(_client_ip(request)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "too many requests, please try again shortly",
                "code": "rate_limited",
            },
        )


def signin_rate_limit(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    """Dependency: trip when sign-in attempts exceed 10/min/IP."""
    _enforce(_signin_limiter, request, settings)


def signup_rate_limit(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    """Dependency: trip when sign-up attempts exceed 5/min/IP."""
    _enforce(_signup_limiter, request, settings)
