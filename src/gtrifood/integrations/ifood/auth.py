"""OAuth client_credentials para iFood Developer API (modelo Centralizada).

Fluxo:
1. POST /authentication/v1.0/oauth/token com grant_type=client_credentials
2. Recebe access_token (TTL ~3h) + expiresIn
3. Cacheia em memória; renova quando faltar <5min para expirar

Referência: https://developer.ifood.com.br/pt-BR/docs/references/authentication/
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from gtrifood.config import Settings, get_settings


@dataclass
class AccessToken:
    token: str
    expires_at: float  # unix timestamp

    @property
    def is_expired(self) -> bool:
        # Margem de 5min para renovar antes de expirar
        return time.time() >= (self.expires_at - 300)


class IFoodAuthError(Exception):
    """Erro ao autenticar com iFood Developer API."""


class IFoodAuthClient:
    """Gerencia obtenção e cache do access_token iFood (client_credentials grant)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._token: AccessToken | None = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _fetch_token(self) -> AccessToken:
        data = {
            "grantType": "client_credentials",
            "clientId": self._settings.ifood_client_id.get_secret_value(),
            "clientSecret": self._settings.ifood_client_secret.get_secret_value(),
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self._settings.ifood_auth_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if response.status_code != 200:
            raise IFoodAuthError(
                f"Falha na autenticação iFood [{response.status_code}]: {response.text}"
            )

        payload = response.json()
        return AccessToken(
            token=payload["accessToken"],
            expires_at=time.time() + payload["expiresIn"],
        )

    async def get_token(self) -> str:
        """Retorna access_token válido (renova se necessário)."""
        if self._token is None or self._token.is_expired:
            self._token = await self._fetch_token()
        return self._token.token
