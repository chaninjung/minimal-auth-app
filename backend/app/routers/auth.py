"""Auth endpoints — POST /api/auth/{signup,signin,signout}.

Design notes:

* The public response DTO (``UserView``) never includes the password
  hash. Handlers project from ``store.User`` to ``UserView`` so an
  accidental field addition in the DB layer cannot leak through.
* Sign-in returns the same opaque error for "no such user" and "wrong
  password" so an attacker cannot enumerate valid emails.
* The 401 path runs argon2id unconditionally — even when the user
  does not exist — so the response timing does not depend on whether
  the email is registered.
* The auth token is delivered as a HttpOnly, ``SameSite=Lax`` cookie.
  This keeps it out of JavaScript reach (XSS-resistant) and removes
  the need for the frontend to manage token storage.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.config import Settings, get_settings
from app.deps import COOKIE_NAME, get_dummy_hash, get_store
from app.rate_limit import signin_rate_limit, signup_rate_limit
from app.schemas import Credentials, UserView
from app.services.password import check_password, hash_password
from app.services.token import issue_token
from app.store import EmailTakenError, Store, UserNotFoundError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    response_model=UserView,
    dependencies=[Depends(signup_rate_limit)],
)
def signup(
    body: Credentials,
    store: Store = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> UserView:
    hashed = hash_password(
        body.password,
        time_cost=settings.argon2_time_cost,
        memory_cost=settings.argon2_memory_cost,
        parallelism=settings.argon2_parallelism,
    )
    try:
        user = store.create_user(body.email, hashed)
    except EmailTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "email is already registered",
                "code": "email_taken",
            },
        )
    return UserView(id=user.id, email=user.email)


@router.post(
    "/signin",
    response_model=UserView,
    dependencies=[Depends(signin_rate_limit)],
)
def signin(
    body: Credentials,
    response: Response,
    store: Store = Depends(get_store),
    settings: Settings = Depends(get_settings),
    dummy_hash: str = Depends(get_dummy_hash),
) -> UserView:
    # Constant-time-ish: ALWAYS run argon2id, even if the user
    # doesn't exist, so the 401 response time doesn't reveal whether
    # the email is registered. We compare against a pre-baked dummy
    # hash that no password will match.
    try:
        user = store.user_by_email(body.email)
        password_hash = user.password_hash
    except UserNotFoundError:
        user = None
        password_hash = dummy_hash

    is_valid = check_password(password_hash, body.password)

    if user is None or not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid credentials", "code": "invalid_credentials"},
        )

    token, exp = issue_token(
        settings.jwt_secret, user.id, user.email, settings.token_ttl
    )
    _set_auth_cookie(response, token, exp, settings)
    return UserView(id=user.id, email=user.email)


@router.post("/signout", status_code=status.HTTP_204_NO_CONTENT)
def signout(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> Response:
    """Stateless: there is no server-side session to invalidate.

    Sign-out is purely about the client losing its token. With
    refresh-token rotation we'd also revoke the refresh family in
    Redis (REPORT.md §3, §7).
    """
    _clear_auth_cookie(response, settings)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


# --- Cookie helpers --------------------------------------------------------


def _set_auth_cookie(
    response: Response,
    token: str,
    exp: datetime,
    settings: Settings,
) -> None:
    max_age = max(0, int((exp - datetime.now(timezone.utc)).total_seconds()))
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def _clear_auth_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
