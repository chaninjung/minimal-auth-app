"""HTTP-level tests for /api/auth/* and /api/me.

We boot the real FastAPI app against a temp SQLite database. Using the
real DB rather than a mock is deliberate — the unique-violation mapping
is one of the things most likely to drift, and a stub would not catch it.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path):
    settings = Settings(
        db_path=str(tmp_path / "test.db"),
        # Tiny argon2 parameters keep the suite fast.
        argon2_time_cost=1,
        argon2_memory_cost=8,
        argon2_parallelism=1,
        jwt_secret="test-secret",
        cookie_secure=False,
        token_ttl_seconds=60,
        rate_limit_enabled=False,  # don't trip rate limit during tests
    )
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


# --- Sign-up ---------------------------------------------------------------


def test_signup_created(client: TestClient):
    r = client.post(
        "/api/auth/signup",
        json={"email": "test@example.com", "password": "hunter2hunter2"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == "test@example.com"
    assert isinstance(body["id"], int)


def test_signup_duplicate_conflict(client: TestClient):
    body = {"email": "dup@example.com", "password": "hunter2hunter2"}
    assert client.post("/api/auth/signup", json=body).status_code == 201
    r = client.post("/api/auth/signup", json=body)
    assert r.status_code == 409
    assert r.json()["code"] == "email_taken"


def test_signup_duplicate_case_insensitive(client: TestClient):
    """Emails are stored COLLATE NOCASE — registering CASE@x.com after
    case@x.com must conflict, not silently shadow.
    """
    assert (
        client.post(
            "/api/auth/signup",
            json={"email": "case@example.com", "password": "hunter2hunter2"},
        ).status_code
        == 201
    )
    r = client.post(
        "/api/auth/signup",
        json={"email": "CASE@example.com", "password": "hunter2hunter2"},
    )
    assert r.status_code == 409


def test_signup_invalid_email(client: TestClient):
    r = client.post(
        "/api/auth/signup",
        json={"email": "no-at-sign", "password": "hunter2hunter2"},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "validation_failed"


def test_signup_short_password(client: TestClient):
    r = client.post(
        "/api/auth/signup",
        json={"email": "x@y.com", "password": "short"},
    )
    assert r.status_code == 422


# --- Sign-in ---------------------------------------------------------------


def test_signin_ok_sets_cookie(client: TestClient):
    body = {"email": "log@example.com", "password": "hunter2hunter2"}
    assert client.post("/api/auth/signup", json=body).status_code == 201
    r = client.post("/api/auth/signin", json=body)
    assert r.status_code == 200
    assert "rk_token" in r.cookies
    cookie_value = r.cookies["rk_token"]
    assert cookie_value  # JWT, non-empty


def test_signin_bad_password_generic_error(client: TestClient):
    body = {"email": "bp@example.com", "password": "hunter2hunter2"}
    assert client.post("/api/auth/signup", json=body).status_code == 201
    r = client.post(
        "/api/auth/signin",
        json={"email": "bp@example.com", "password": "wrongwrongwrong"},
    )
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_credentials"


def test_signin_unknown_user_same_error(client: TestClient):
    """Must look identical to "wrong password" so the response cannot
    be used to enumerate registered emails."""
    r = client.post(
        "/api/auth/signin",
        json={"email": "ghost@example.com", "password": "hunter2hunter2"},
    )
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_credentials"


# --- /me + sign-out --------------------------------------------------------


def test_me_requires_auth(client: TestClient):
    r = client.get("/api/me")
    assert r.status_code == 401


def test_signout_returns_204(client: TestClient):
    r = client.post("/api/auth/signout")
    assert r.status_code == 204


# --- Full integration flow -------------------------------------------------


def test_full_flow_signup_signin_me_signout(client: TestClient):
    """End-to-end: sign up → sign in → /me → sign out → /me 401."""
    body = {"email": "flow@example.com", "password": "hunter2hunter2"}

    assert client.post("/api/auth/signup", json=body).status_code == 201

    r = client.post("/api/auth/signin", json=body)
    assert r.status_code == 200

    # The TestClient persists cookies across requests.
    r = client.get("/api/me")
    assert r.status_code == 200
    assert r.json()["email"] == "flow@example.com"

    assert client.post("/api/auth/signout").status_code == 204

    # Cookie cleared — /me must now fail.
    r = client.get("/api/me")
    assert r.status_code == 401
