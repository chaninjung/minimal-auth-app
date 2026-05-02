"""FastAPI dependency injection helpers.

These are FastAPI's idiomatic alternative to Go's middleware: a function
declared as a parameter dependency runs before the handler, can short-
circuit by raising :class:`HTTPException`, and its return value is
injected into the handler.
"""

from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, Request, status

from app.config import Settings, get_settings
from app.services.token import Claims, TokenError, parse_token
from app.store import Store

# Centralised so handlers and tests never disagree on the cookie name.
COOKIE_NAME = "rk_token"


def get_store(request: Request) -> Store:
    """Pull the Store the lifespan attached to ``app.state``."""
    return request.app.state.store


def get_dummy_hash(request: Request) -> str:
    """Pre-baked bcrypt hash used for constant-time signin failures."""
    return request.app.state.dummy_hash


def get_current_claims(
    rk_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
    settings: Settings = Depends(get_settings),
) -> Claims:
    """Auth gate — extracts and verifies the JWT from a HttpOnly cookie.

    On any failure (missing cookie, bad signature, expired, etc.) we
    return a generic 401. We intentionally do not tell the caller which
    step failed — that information is for our logs, not the attacker.
    """
    if not rk_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "authentication required", "code": "unauthenticated"},
        )
    try:
        return parse_token(settings.jwt_secret, rk_token)
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "authentication required", "code": "invalid_token"},
        )
