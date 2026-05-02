"""Pydantic models — request bodies, response DTOs, error envelope.

These are the wire contract. They must match the TypeScript types on
the frontend in ``src/api/auth.ts`` and the zod schema in
``src/lib/schemas.ts``. We keep them in sync by hand at this surface
size; see REPORT.md §5 for the discussion of OpenAPI codegen at scale.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator


class Credentials(BaseModel):
    """Sign-up / sign-in body.

    Validation rules mirror the frontend zod schema. The frontend
    validates eagerly to give fast feedback; the backend re-validates
    because we never trust the client.

    ``EmailStr`` runs a real RFC 5321 / 5322 check via the
    ``email-validator`` library — much stricter than a substring check
    on '@', and matches the ``z.string().email()`` rule on the frontend.
    """

    email: EmailStr = Field(..., max_length=254)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("email", mode="after")
    @classmethod
    def _normalise_email(cls, v: str) -> str:
        # Lower-case so "Foo@Bar.com" and "foo@bar.com" don't create
        # two accounts. The DB column is also COLLATE NOCASE for safety.
        return v.strip().lower()


class UserView(BaseModel):
    """Public projection of a user — never includes the password hash."""

    id: int
    email: str


class ErrorBody(BaseModel):
    """Standard error envelope.

    ``error`` is a short human-readable message; ``code`` is an optional
    machine-readable identifier the frontend can branch on (e.g.
    ``email_taken``, ``invalid_credentials``).
    """

    error: str
    code: str | None = None
