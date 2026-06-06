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

    # ===== Interrupções (pausas da loja) =====
    async def list_interruptions(self, merchant_id: str) -> list[dict[str, Any]]:
        """Lista pausas ativas e futuras."""
        result = await self._client.get(
            f"/merchant/v1.0/merchants/{merchant_id}/interruptions"
        )
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("interruptions", [])
        return []

    async def create_interruption(
        self,
        merchant_id: str,
        *,
        description: str,
        start: str,           # ISO datetime
        end: str,             # ISO datetime
    ) -> dict[str, Any] | None:
        """Cria uma pausa. start/end em ISO 8601 com timezone."""
        body = {"description": description, "start": start, "end": end}
        return await self._client.post(
            f"/merchant/v1.0/merchants/{merchant_id}/interruptions",
            json=body,
        )

    async def delete_interruption(
        self,
        merchant_id: str,
        interruption_id: str,
    ) -> None:
        """Remove uma pausa pelo ID."""
        await self._client.request(
            "DELETE",
            f"/merchant/v1.0/merchants/{merchant_id}/interruptions/{interruption_id}",
        )

    # ===== Horário de funcionamento =====
    async def get_opening_hours(self, merchant_id: str) -> dict[str, Any]:
        """Retorna horários de funcionamento por dia da semana."""
        result = await self._client.get(
            f"/merchant/v1.0/merchants/{merchant_id}/opening-hours"
        )
        return result or {}

    async def update_opening_hours(
        self,
        merchant_id: str,
        shifts: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Substitui horários por uma lista de shifts.

        Cada shift: { dayOfWeek, start: 'HH:MM:SS', duration: minutos }
        Ex: sábado 10-19 = { dayOfWeek: 'SATURDAY', start: '10:00:00', duration: 540 }
        """
        body = {"shifts": shifts}
        return await self._client.request(
            "PUT",
            f"/merchant/v1.0/merchants/{merchant_id}/opening-hours",
            json=body,
        )
