"""Cliente HTTP base para iFood Developer API.

Centraliza headers, base URL, autenticação e tratamento de erros.
Módulos específicos (merchants, orders, financial, reviews) usam esse cliente.
"""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from gtrifood.config import Settings, get_settings
from gtrifood.integrations.ifood.auth import IFoodAuthClient


class IFoodAPIError(Exception):
    """Erro de chamada à API iFood (status >= 400)."""

    def __init__(self, status_code: int, message: str, body: Any = None) -> None:
        super().__init__(f"[{status_code}] {message}")
        self.status_code = status_code
        self.body = body


class IFoodClient:
    """Cliente HTTP autenticado para a API iFood."""

    def __init__(
        self,
        settings: Settings | None = None,
        auth: IFoodAuthClient | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._auth = auth or IFoodAuthClient(self._settings)

    async def _headers(self) -> dict[str, str]:
        token = await self._auth.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.TransportError),
        reraise=True,
    )
    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        url = f"{self._settings.ifood_api_base_url}{path}"
        headers = await self._headers()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, params=params, json=json, headers=headers)

        if response.status_code == 204:
            return None
        if not response.is_success:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise IFoodAPIError(response.status_code, response.reason_phrase, body)
        if response.status_code == 200 and response.content:
            return response.json()
        return None

    async def get(self, path: str, **kwargs: Any) -> Any:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> Any:
        return await self.request("POST", path, **kwargs)
