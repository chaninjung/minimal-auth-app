"""Password hashing.

bcrypt was chosen because it is purpose-built for password storage:
slow by design, automatic per-hash salt, tunable work factor. The hash
itself encodes the algorithm and cost, so future cost rotations can be
done lazily on next login.
"""

from __future__ import annotations

import bcrypt


def hash_password(password: str, rounds: int = 12) -> str:
    """Return a bcrypt hash. ``rounds`` is the cost log2 (12 ≈ 250ms).

    Tests use ``rounds=4`` to keep the suite fast.
    """
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def check_password(hashed: str, password: str) -> bool:
    """Verify a password.

    ``bcrypt.checkpw`` does a constant-time comparison with respect to
    the password length, so it does not leak timing information about
    correctness. Malformed hashes return ``False`` rather than raising
    so the caller does not need a try/except for error paths.
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
