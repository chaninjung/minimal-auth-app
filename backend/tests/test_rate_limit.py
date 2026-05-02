"""Rate-limit tests.

We boot the app with rate limiting *enabled* and hammer signin past
its per-IP budget to confirm that the 11th request returns 429 with
the standard ``{error, code}`` envelope.
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
        bcrypt_rounds=4,
        jwt_secret="test-secret",
        cookie_secure=False,
        token_ttl_seconds=60,
        rate_limit_enabled=True,  # <-- enabled for this suite
    )
    # Reset module-level limiter state between fixture instantiations so
    # a previous test's hits don't bleed into this one. The limiters are
    # private; we reach in deliberately because this is the test seam.
    from app import rate_limit
    rate_limit._signin_limiter._buckets.clear()
    rate_limit._signup_limiter._buckets.clear()

    app = create_app(settings)
    with TestClient(app) as c:
        yield c


def test_signin_rate_limit_trips_after_budget(client: TestClient):
    """The 11th sign-in attempt within a minute should return 429."""
    body = {"email": "rl@example.com", "password": "wrong-on-purpose"}

    # First 10 attempts: 401 (invalid credentials), each "uses" one slot.
    for i in range(10):
        r = client.post("/api/auth/signin", json=body)
        assert r.status_code == 401, f"attempt {i + 1}: {r.status_code} {r.text}"

    # The 11th: rate-limited.
    r = client.post("/api/auth/signin", json=body)
    assert r.status_code == 429
    assert r.json()["code"] == "rate_limited"


def test_signup_rate_limit_trips_after_budget(client: TestClient):
    """The 6th sign-up attempt within a minute should return 429."""
    # First 5 valid signups (different emails so no 409 conflict).
    for i in range(5):
        r = client.post(
            "/api/auth/signup",
            json={"email": f"rl{i}@example.com", "password": "hunter2hunter2"},
        )
        assert r.status_code == 201, f"attempt {i + 1}: {r.status_code}"

    # The 6th: rate-limited.
    r = client.post(
        "/api/auth/signup",
        json={"email": "rl6@example.com", "password": "hunter2hunter2"},
    )
    assert r.status_code == 429
    assert r.json()["code"] == "rate_limited"
