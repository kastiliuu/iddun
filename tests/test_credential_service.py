"""Regressões da proteção de credenciais OAuth; sem segredo real."""
import base64

import pytest
from cryptography.fernet import Fernet

from app.services.credential_service import decrypt_secret, encrypt_secret


def test_credential_round_trip_uses_encryption_and_handles_empty(app):
    with app.app_context():
        assert encrypt_secret(None) is None
        assert decrypt_secret(None) is None
        assert encrypt_secret("") is None
        assert decrypt_secret("") is None

        plaintext = "oauth-secret-ê-🥇"
        encrypted = encrypt_secret(plaintext)
        assert isinstance(encrypted, str)
        assert encrypted != plaintext
        assert plaintext not in encrypted
        assert decrypt_secret(encrypted) == plaintext


@pytest.mark.parametrize("configured", [False, True])
def test_credential_key_derivation_is_stable_for_same_configuration(app, configured):
    with app.app_context():
        app.config["SECRET_KEY"] = "fallback-secret-a"
        app.config["TOKEN_ENCRYPTION_KEY"] = (
            "configured-encryption-secret" if configured else None
        )
        encrypted = encrypt_secret("refresh-token")
        assert decrypt_secret(encrypted) == "refresh-token"
        assert decrypt_secret(encrypt_secret("refresh-token")) == "refresh-token"


def test_credential_uses_explicit_fernet_key_when_configured(app):
    key = Fernet.generate_key().decode("ascii")
    with app.app_context():
        app.config["TOKEN_ENCRYPTION_KEY"] = key
        token = encrypt_secret("google-refresh")
        assert Fernet(key.encode()).decrypt(token.encode()).decode() == "google-refresh"


def test_credential_key_rotation_rejects_ciphertext_without_leaking_secret(app):
    with app.app_context():
        app.config["TOKEN_ENCRYPTION_KEY"] = "old-encryption-key"
        cipher = encrypt_secret("private-oauth-refresh")
        app.config["TOKEN_ENCRYPTION_KEY"] = "new-encryption-key"
        with pytest.raises(RuntimeError, match="Não foi possível descriptografar") as error:
            decrypt_secret(cipher)
        assert "private-oauth-refresh" not in str(error.value)


def test_credential_corrupted_ciphertext_raises_safe_error(app):
    with app.app_context():
        with pytest.raises(RuntimeError, match="Não foi possível descriptografar"):
            decrypt_secret("not-a-fernet-token")


def test_credential_without_configured_keys_rejects_encryption(app):
    with app.app_context():
        app.config["TOKEN_ENCRYPTION_KEY"] = None
        app.config["SECRET_KEY"] = None
        with pytest.raises(RuntimeError, match="SECRET_KEY não está configurada"):
            encrypt_secret("sensitive-token")
