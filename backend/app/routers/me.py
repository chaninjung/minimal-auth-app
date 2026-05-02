"""GET /api/me — the protected endpoint that returns the authenticated user.

Auth is enforced by ``get_current_claims`` (see ``deps.py``), which
extracts and verifies the JWT from the HttpOnly cookie. By the time
the handler runs, the request is guaranteed authenticated.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_current_claims, get_store
from app.schemas import UserView
from app.services.token import Claims
from app.store import Store, UserNotFoundError

router = APIRouter(tags=["me"])


@router.get("/me", response_model=UserView)
def get_me(
    claims: Claims = Depends(get_current_claims),
    store: Store = Depends(get_store),
) -> UserView:
    """Re-fetch from the DB rather than trusting only the token.

    This means a deleted user invalidates immediately on the next /me
    call even though the JWT is still cryptographically valid — a small
    consolation against the lack of a revocation list (see REPORT §2).
    """
    try:
        user = store.user_by_id(claims.user_id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "authentication required", "code": "unauthenticated"},
        )
    return UserView(id=user.id, email=user.email)
