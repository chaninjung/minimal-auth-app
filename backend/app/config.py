"""Runtime configuration loaded from environment variables.

All values have safe defaults so the server can boot bare; see README.md
for production-grade overrides. Anything that would change between local
dev, CI, and production lives here, so handlers/services never read
``os.environ`` directly. That keeps them trivially testable — see
``tests/test_auth.py`` where Settings is constructed directly.
"""

from __future__ import annotations

from datetime import timedelta

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Resolved runtime configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Server -------------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8080

    # --- Database -----------------------------------------------------------
    db_path: str = "data.db"

    # --- JWT ----------------------------------------------------------------
    # WARNING: override in any non-dev environment. The boot sequence does
    # not refuse to start on the default — that's a documented production
    # hardening point in REPORT.md §2.
    jwt_secret: str = "dev-secret-change-me"
    token_ttl_seconds: int = 24 * 60 * 60  # 24h

    # --- Cookie / CORS ------------------------------------------------------
    # Single, explicit origin — no wildcards. Credentials are on so the
    # browser sends our HttpOnly auth cookie cross-origin.
    allowed_origin: str = "http://localhost:5173"
    # Set ``true`` behind HTTPS so the cookie carries the Secure flag.
    cookie_secure: bool = False

    # --- Password hashing ---------------------------------------------------
    # bcrypt work factor (cost = 2^rounds). Tests override to 4 for speed.
    bcrypt_rounds: int = 12

    @property
    def token_ttl(self) -> timedelta:
        return timedelta(seconds=self.token_ttl_seconds)


def get_settings() -> Settings:
    """Construct fresh Settings — re-reads env on every call.

    FastAPI caches dependency results within a request, so this is only
    invoked once per request even when many handlers depend on it.
    """
    return Settings()
