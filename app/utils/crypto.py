import os
import base64
import hashlib
from cryptography.fernet import Fernet
from flask import current_app


def get_fernet_instance() -> Fernet:
    """Obtém ou instancia o Fernet com base na chave de configuração ou derivada do SECRET_KEY."""
    custom_key = None
    if current_app:
        custom_key = current_app.config.get("FERNET_KEY") or current_app.config.get("SECRET_KEY")
    if not custom_key:
        custom_key = os.getenv("FERNET_KEY") or os.getenv("SECRET_KEY", "gapar-fallback-secret-key-default-2026")

    # Garante chave url-safe base64 de 32 bytes (256 bits)
    derived_bytes = hashlib.sha256(custom_key.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(derived_bytes)
    return Fernet(fernet_key)


def encrypt_token(raw_token: str | None) -> str | None:
    """Cifra um token antes de salvar no banco de dados (RNF08)."""
    if not raw_token:
        return None
    f = get_fernet_instance()
    return f.encrypt(raw_token.encode("utf-8")).decode("utf-8")


def decrypt_token(cipher_text: str | None) -> str | None:
    """Decifra um token armazenado no banco de dados (RNF08)."""
    if not cipher_text:
        return None
    try:
        f = get_fernet_instance()
        return f.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except Exception:
        # Se falhar (ex: texto antigo não criptografado ou chave alterada)
        return None
