"""Unit tests for the password service."""

from app.services.password import check_password, hash_password


def test_hash_and_check_roundtrip():
    pw = "hunter2hunter2"
    h = hash_password(pw, rounds=4)  # low cost for test speed
    assert h
    assert h != pw
    assert check_password(h, pw) is True
    assert check_password(h, "wrong-password") is False


def test_hash_unique_per_call():
    """bcrypt salts each call, so the same password produces distinct hashes.

    This guards against accidental salt reuse — a regression here would
    let an attacker correlate identical passwords across users.
    """
    a = hash_password("samesame", rounds=4)
    b = hash_password("samesame", rounds=4)
    assert a != b


def test_check_handles_malformed_hash():
    """A garbage 'hash' should return False, not raise."""
    assert check_password("not-a-real-hash", "password") is False
    assert check_password("", "password") is False
