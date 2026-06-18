from datetime import timedelta

import pytest

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_does_not_store_plaintext():
    hashed = hash_password("super-secret-123")
    assert hashed != "super-secret-123"
    assert verify_password("super-secret-123", hashed)


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("super-secret-123")
    assert not verify_password("wrong-password", hashed)


def test_access_token_round_trip():
    token = create_access_token("user@example.com")
    payload = decode_token(token)
    assert payload["sub"] == "user@example.com"
    assert payload["type"] == "access"


def test_refresh_token_round_trip():
    token = create_refresh_token("user@example.com")
    payload = decode_token(token)
    assert payload["sub"] == "user@example.com"
    assert payload["type"] == "refresh"


def test_decode_token_rejects_garbage():
    with pytest.raises(ValueError):
        decode_token("not-a-real-token")
