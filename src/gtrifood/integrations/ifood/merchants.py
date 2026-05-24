"""Endpoints do módulo Merchant da API iFood.

Referência: https://developer.ifood.com.br/pt-BR/docs/references/merchant/
"""

from __future__ import annotations

from typing import Any

from gtrifood.integrations.ifood.client import IFoodClient


class MerchantAPI:
    def __init__(self, client: IFoodClient) -> None:
        self._client = client

    async def list_merchants(self) -> list[dict[str, Any]]:
        """Lista todos os merchants autorizados para esse app (Centralizada)."""
        result = await self._client.get("/merchant/v1.0/merchants")
        return result or []

    async def get_merchant(self, merchant_id: str) -> dict[str, Any]:
        """Detalhes completos de um merchant."""
        return await self._client.get(f"/merchant/v1.0/merchants/{merchant_id}")

    async def get_status(self, merchant_id: str) -> list[dict[str, Any]]:
        """Status operacional do merchant (aberto/fechado, módulos ativos)."""
        return await self._client.get(f"/merchant/v1.0/merchants/{merchant_id}/status") or []
