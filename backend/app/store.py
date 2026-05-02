"""SQLite persistence layer.

SQLite was chosen because it requires zero setup (single file) and
Python's stdlib ``sqlite3`` driver means no external dependencies for
the data tier. In production this would be swapped for Postgres — the
public surface (``create_user``, ``user_by_email``, ``user_by_id``) is
small enough to become an ABC/Protocol, allowing the swap without
touching handlers.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime


# --- Errors ----------------------------------------------------------------
# Driver-specific errors are mapped into these so callers don't need to
# know about SQLite internals.
class StoreError(Exception):
    """Base store error."""


class EmailTakenError(StoreError):
    """Email already registered (UNIQUE constraint violation)."""


class UserNotFoundError(StoreError):
    """No user with the given identifier."""


@dataclass(frozen=True)
class User:
    """A user row.

    ``password_hash`` is included because authentication needs it; handlers
    project to ``UserView`` (in ``schemas.py``) before responding so the
    hash never leaves the backend.
    """

    id: int
    email: str
    password_hash: str
    created_at: datetime


class Store:
    """SQLite-backed user repository."""

    def __init__(self, path: str) -> None:
        # ``check_same_thread=False`` lets the worker threads share the
        # connection. ``isolation_level=None`` puts us in autocommit mode;
        # SQLite serialises writes internally, adequate at this scale.
        self._conn = sqlite3.connect(
            path, check_same_thread=False, isolation_level=None
        )
        self._conn.row_factory = sqlite3.Row
        # WAL gives better concurrency than the default rollback journal.
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        self._conn.close()

    def migrate(self) -> None:
        """Create tables if missing. Idempotent — safe every boot."""
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def create_user(self, email: str, password_hash: str) -> User:
        """Insert a new user.

        Raises :class:`EmailTakenError` on duplicate (case-insensitive,
        thanks to ``COLLATE NOCASE`` on the column).
        """
        try:
            cur = self._conn.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (email, password_hash),
            )
        except sqlite3.IntegrityError as e:
            # The driver reports unique violations as a plain error
            # containing "UNIQUE constraint failed". Matching on the
            # message is brittle, so this is the one place that knows
            # the driver-specific phrasing.
            if "UNIQUE constraint failed" in str(e):
                raise EmailTakenError(email) from e
            raise
        return self.user_by_id(cur.lastrowid or 0)

    def user_by_email(self, email: str) -> User:
        row = self._conn.execute(
            "SELECT id, email, password_hash, created_at "
            "FROM users WHERE email = ? COLLATE NOCASE",
            (email,),
        ).fetchone()
        if row is None:
            raise UserNotFoundError(email)
        return _row_to_user(row)

    def user_by_id(self, user_id: int) -> User:
        row = self._conn.execute(
            "SELECT id, email, password_hash, created_at "
            "FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            raise UserNotFoundError(str(user_id))
        return _row_to_user(row)


def _row_to_user(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        email=row["email"],
        password_hash=row["password_hash"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )
