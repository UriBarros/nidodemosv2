"""Helpers de segurança — encriptação simétrica para tokens/secrets sensíveis."""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet

from gtrifood.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    key = get_settings().encryption_key.get_secret_value().encode()
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    """Cifra string com Fernet. Retorna base64 URL-safe."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decifra string Fernet."""
    return _fernet().decrypt(ciphertext.encode()).decode()
