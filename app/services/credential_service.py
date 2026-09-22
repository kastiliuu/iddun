import base64
import hashlib

from flask import current_app


def _fernet():
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:
        raise RuntimeError(
            "A dependência 'cryptography' é necessária para proteger credenciais OAuth. "
            "Execute pip install -r requirements.txt."
        ) from exc

    configured = current_app.config.get("TOKEN_ENCRYPTION_KEY")
    if configured:
        raw = configured.encode("utf-8")
        try:
            decoded = base64.urlsafe_b64decode(raw)
            key = raw if len(decoded) == 32 else base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
        except Exception:
            key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    else:
        secret = current_app.config.get("SECRET_KEY")
        if not secret:
            raise RuntimeError("SECRET_KEY não está configurada para criptografar credenciais.")
        key = base64.urlsafe_b64encode(hashlib.sha256(str(secret).encode("utf-8")).digest())
    return Fernet(key)


def encrypt_secret(value):
    if not value:
        return None
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value):
    if not value:
        return None
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        raise RuntimeError("Não foi possível descriptografar a credencial armazenada.") from exc
