"""Structured logging via structlog, with per-request correlation IDs.

Two pieces wired together:

1. :func:`configure` sets up ``structlog`` to emit JSON one line per
   log event, with timestamps, log level, and any context bound to
   the logger via :func:`structlog.contextvars.bind_contextvars`.

2. :class:`RequestContextMiddleware` mints a UUID per inbound request
   and binds it (plus the method and path) to the contextvar context.
   Every log line emitted while handling that request automatically
   carries those fields, so the operator can grep one ``request_id``
   to follow a request through the whole stack — invaluable in
   production.

Why structlog over stdlib ``logging`` alone:

* Free-form ``key=value`` context — no string interpolation or extra
  ``LogRecord`` plumbing.
* JSON output is one renderer call away (``JSONRenderer``), making it
  ready for any log aggregator (Datadog, Loki, CloudWatch).
* Plays nicely with stdlib ``logging``: uvicorn's access log is
  re-emitted through the same pipeline if we want.
"""

from __future__ import annotations

import logging
import sys
import uuid
from typing import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def configure(level: str = "INFO") -> None:
    """Configure structlog to emit JSON to stdout.

    Idempotent — safe to call multiple times.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Stdlib logging gets a plain handler so anything that goes through
    # ``logging`` (e.g. uvicorn) ends up on stdout too.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Bind a per-request UUID + method + path to the structlog context.

    Every log line emitted while handling the request carries these
    fields automatically. The same UUID is also attached to the
    response as ``X-Request-ID`` so a client (or a load-balancer) can
    pin-point a request in the logs.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        try:
            response = await call_next(request)
        finally:
            # The contextvar is cleared at the next request anyway, but
            # being explicit keeps log lines from background tasks clean.
            structlog.contextvars.clear_contextvars()
        response.headers["X-Request-ID"] = request_id
        return response
