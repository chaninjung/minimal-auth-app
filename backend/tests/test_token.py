"""Unit tests for the JWT token service."""

import base64
import json
from datetime import timedelta

import pytest

from app.services.token import TokenError, issue_token, parse_token


def test_issue_and_parse_roundtrip():
    secret = "test-secret"
    token, exp = issue_token(secret, 42, "x@example.com", timedelta(minutes=1))
    assert token  # non-empty
    claims = parse_token(secret, token)
    assert claims.user_id == 42
    assert claims.email == "x@example.com"
    assert claims.exp > claims.iat


def test_parse_wrong_secret_rejects():
    token, _ = issue_token("a", 1, "x@y.com", timedelta(minutes=1))
    with pytest.raises(TokenError):
        parse_token("b", token)


def test_parse_expired_rejects():
    token, _ = issue_token("s", 1, "x@y.com", timedelta(seconds=-1))
    with pytest.raises(TokenError):
        parse_token("s", token)


def test_parse_garbage_rejects():
    with pytest.raises(TokenError):
        parse_token("s", "not-a-real-jwt")


def test_parse_alg_none_rejects():
    """Classic JWT confusion attack: a token with header {alg: none}
    and no signature must be rejected.

    PyJWT's ``algorithms=["HS256"]`` keyword in :func:`parse_token`
    closes this — any token whose header advertises a different alg
    is refused before signature checking.
    """

    def b64(obj: dict) -> bytes:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=")

    header = b64({"alg": "none", "typ": "JWT"})
    payload = b64({"uid": 1, "email": "x@y.com", "exp": 9999999999})
    token = (header + b"." + payload + b".").decode()

    with pytest.raises(TokenError):
        parse_token("any-secret", token)
