"""JWT issuance and verification.

We use HS256 (HMAC-SHA256) — the secret is shared between the issuer
and the verifier, which is fine for a single-service auth tier.
Switching to RS256 (asymmetric) would only matter if a separate party
needed to verify tokens without holding the issuing secret.

Claims carry only ``user_id`` and ``email`` — anything more would couple
the token to mutable user state. ``user_id`` is the source of truth;
``email`` is included to populate the UI without an extra DB hit (still
re-validated against the DB on ``GET /api/me``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt


class TokenError(Exception):
    """Verification or parsing failure (signature, expiry, format, …)."""


@dataclass(frozen=True)
class Claims:
    user_id: int
    email: str
    exp: datetime
    iat: datetime


def issue_token(
    secret: str, user_id: int, email: str, ttl: timedelta
) -> tuple[str, datetime]:
    """Sign a new JWT and return ``(token, absolute_expiry)``."""
    now = datetime.now(timezone.utc)
    exp = now + ttl
    payload: dict[str, object] = {
        "uid": user_id,
        "email": email,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "iss": "minimal-auth",
        "sub": email,
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token, exp


def parse_token(secret: str, raw: str) -> Claims:
    """Verify signature, expiry, and algorithm; return claims.

    The ``algorithms=["HS256"]`` argument is the critical defence
    against the classic "alg=none" / RSA-as-HMAC confusion attacks:
    PyJWT will refuse any token whose header advertises a different
    algorithm.
    """
    try:
        payload = jwt.decode(raw, secret, algorithms=["HS256"])
    except jwt.PyJWTError as e:
        raise TokenError(str(e)) from e

    return Claims(
        user_id=int(payload["uid"]),
        email=str(payload["email"]),
        exp=datetime.fromtimestamp(int(payload["exp"]), tz=timezone.utc),
        iat=datetime.fromtimestamp(int(payload["iat"]), tz=timezone.utc),
    )
