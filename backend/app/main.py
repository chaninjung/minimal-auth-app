"""Application entry point.

Builds the FastAPI app, wires the store, registers routes, and (when
run directly) starts uvicorn. The :func:`create_app` factory takes an
optional ``Settings`` so tests can construct an isolated app instance
with a temp DB and a fast bcrypt cost — see ``tests/test_auth.py``.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import bcrypt
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.routers import auth as auth_router
from app.routers import me as me_router
from app.store import Store


def create_app(settings: Settings | None = None) -> FastAPI:
    """Composition root.

    Wires config → store → routers. Tests pass an explicit ``settings``
    to bind to a temp DB without touching real env vars.
    """
    if settings is None:
        settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Open the DB and run idempotent migrations.
        store = Store(settings.db_path)
        store.migrate()
        app.state.store = store

        # Pre-bake a bcrypt hash at the configured cost. We use it on
        # the signin failure path when the user doesn't exist, so the
        # response time looks the same whether the email is registered
        # or not — closing a timing-based enumeration channel.
        app.state.dummy_hash = bcrypt.hashpw(
            b"_never_matches_",
            bcrypt.gensalt(rounds=settings.bcrypt_rounds),
        ).decode("utf-8")

        yield

        store.close()

    app = FastAPI(title="Minimal Auth App", lifespan=lifespan)

    # Override the cached ``get_settings`` dependency so handlers see
    # whichever settings this factory was built with (tests rely on this).
    app.dependency_overrides[get_settings] = lambda: settings

    # --- CORS -----------------------------------------------------------
    # Single, explicit origin — no wildcards. Credentials on so the
    # browser sends our HttpOnly cookie. In dev, Vite proxies /api/*
    # to the backend (same-origin) so CORS isn't exercised; this config
    # kicks in if the SPA is hosted separately in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.allowed_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
        max_age=300,
    )

    # --- Error envelope -------------------------------------------------
    # Coerce every error to ``{ error, code }`` so the frontend has a
    # single shape to parse.
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": str(exc.detail), "code": "http_error"},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        errors = exc.errors()
        msg = errors[0]["msg"] if errors else "validation failed"
        # Pydantic prefixes Value errors with "Value error, " — strip it.
        msg = msg.removeprefix("Value error, ")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": msg, "code": "validation_failed"},
        )

    # --- Routes ---------------------------------------------------------
    app.include_router(auth_router.router, prefix="/api")
    app.include_router(me_router.router, prefix="/api")

    @app.get("/healthz", status_code=status.HTTP_204_NO_CONTENT)
    def healthz() -> Response:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


# Module-level app for ``uvicorn app.main:app``.
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
    )
