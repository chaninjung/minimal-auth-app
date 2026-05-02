"""Password hashing.

argon2id was chosen over bcrypt for three concrete reasons:

* **Memory-hard.** argon2id forces an attacker to commit RAM per
  guess — GPUs and ASICs lose their cost advantage. bcrypt is only
  CPU-hard.
* **No 72-byte truncation.** bcrypt silently caps input at 72 bytes,
  so any policy that allows longer passwords is misleading. argon2id
  has no such limit.
* **Modern winner.** argon2id won the Password Hashing Competition
  (PHC 2015) and is OWASP's first recommendation in 2024.

Defaults follow OWASP's recommended minimum for argon2id:
``time_cost=3``, ``memory_cost=64 MiB``, ``parallelism=4``. Tests
override to a much smaller configuration to keep the suite fast.

The hash format encodes algorithm + cost + salt + digest, so future
parameter rotations can be detected via ``check_needs_rehash`` and
applied lazily on next login.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

# A standalone verifier — works on any argon2 hash because the params
# are encoded in the hash itself, not on the verifier instance.
_VERIFIER = PasswordHasher()


def hash_password(
    password: str,
    *,
    time_cost: int = 3,
    memory_cost: int = 65536,  # 64 MiB
    parallelism: int = 4,
) -> str:
    """Hash with argon2id at the given cost parameters.

    OWASP-recommended minimum for argon2id (2024) is
    ``time_cost=2, memory_cost=19456, parallelism=1``. We default a
    little higher; tests pass much smaller numbers for speed.
    """
    hasher = PasswordHasher(
        time_cost=time_cost,
        memory_cost=memory_cost,
        parallelism=parallelism,
    )
    return hasher.hash(password)


def check_password(hashed: str, password: str) -> bool:
    """Constant-time verify.

    ``PasswordHasher.verify`` returns ``True`` on match and raises on
    mismatch (or on a malformed/foreign-format hash). We collapse both
    failure modes to ``False`` so callers don't need a try/except.
    """
    try:
        return _VERIFIER.verify(hashed, password)
    except (VerifyMismatchError, InvalidHashError):
        return False
