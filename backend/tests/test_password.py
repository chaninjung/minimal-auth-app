"""Unit tests for the password service (argon2id)."""

from app.services.password import check_password, hash_password

# Tiny parameters so the suite stays fast. Production defaults are far
# larger (see ``app/config.py``).
_FAST = dict(time_cost=1, memory_cost=8, parallelism=1)


def test_hash_and_check_roundtrip():
    pw = "hunter2hunter2"
    h = hash_password(pw, **_FAST)
    assert h
    assert h != pw
    assert h.startswith("$argon2id$")  # confirms the algorithm
    assert check_password(h, pw) is True
    assert check_password(h, "wrong-password") is False


def test_hash_unique_per_call():
    """argon2 generates a fresh salt on every call, so the same input
    must produce different hashes. This guards against accidental
    salt-reuse — a regression here would let an attacker correlate
    identical passwords across users.
    """
    a = hash_password("samesame", **_FAST)
    b = hash_password("samesame", **_FAST)
    assert a != b


def test_check_handles_malformed_hash():
    """A garbage 'hash' should return False, not raise."""
    assert check_password("not-a-real-hash", "password") is False
    assert check_password("", "password") is False
    # A bcrypt hash, fed to the argon2 verifier, is also rejected.
    bcrypt_like = "$2b$04$" + "a" * 53
    assert check_password(bcrypt_like, "password") is False
