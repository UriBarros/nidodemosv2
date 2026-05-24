"""Validação de JWT do Supabase Auth.

Supabase emite JWTs assinados com **ES256** (chave assimétrica ECC P-256).
Buscamos a chave pública via JWKS endpoint público do projeto e cacheamos.

Suporta também HS256 (Legacy JWT Secret) como fallback se `SUPABASE_JWT_SECRET`
estiver setado no .env — útil pra projetos antigos.

JWKS endpoint: `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from functools import lru_cache

import jwt
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError

from gtrifood.config import Settings, get_settings


@dataclass
class AuthUser:
    user_id: uuid.UUID
    email: str | None
    role: str


class AuthError(Exception):
    """Token inválido, expirado ou ausente."""


@lru_cache
def _jwks_client() -> PyJWKClient:
    settings = get_settings()
    jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    # cache_jwk_set=True (default) — biblioteca cacheia em memória
    return PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600)


def _decode_es256(token: str) -> dict:
    """Valida JWT ES256 buscando chave pública via JWKS."""
    client = _jwks_client()
    signing_key = client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256"],
        audience="authenticated",
    )


def _decode_hs256(token: str, settings: Settings) -> dict:
    """Valida JWT HS256 com shared secret (Legacy)."""
    if not settings.supabase_jwt_secret:
        raise AuthError("HS256 mode mas SUPABASE_JWT_SECRET não configurado")
    return jwt.decode(
        token,
        settings.supabase_jwt_secret.get_secret_value(),
        algorithms=["HS256"],
        audience="authenticated",
    )


def decode_supabase_jwt(token: str) -> AuthUser:
    """Valida JWT do Supabase (ES256 via JWKS; HS256 fallback se configurado).

    Raises:
        AuthError: token inválido/expirado.
    """
    settings = get_settings()

    # Detecta algoritmo pelo header do token
    try:
        unverified_header = jwt.get_unverified_header(token)
    except InvalidTokenError as e:
        raise AuthError(f"Token malformado: {e}") from e

    alg = unverified_header.get("alg")

    try:
        if alg == "ES256":
            payload = _decode_es256(token)
        elif alg == "HS256":
            payload = _decode_hs256(token, settings)
        else:
            raise AuthError(f"Algoritmo não suportado: {alg}")
    except InvalidTokenError as e:
        raise AuthError(f"Token inválido: {e}") from e

    sub = payload.get("sub")
    if not sub:
        raise AuthError("Token sem 'sub' (user_id)")
    try:
        user_id = uuid.UUID(sub)
    except ValueError as e:
        raise AuthError(f"'sub' não é UUID válido: {sub}") from e

    return AuthUser(
        user_id=user_id,
        email=payload.get("email"),
        role=payload.get("role", "authenticated"),
    )
