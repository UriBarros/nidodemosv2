"""Endpoints do módulo Order da API iFood."""

from __future__ import annotations

from typing import Any

from gtrifood.integrations.ifood.client import IFoodClient


class OrdersAPI:
    def __init__(self, client: IFoodClient) -> None:
        self._client = client

    async def get_order(self, order_id: str) -> dict[str, Any]:
        """Detalhes completos do pedido (após receber evento PLC, buscar aqui)."""
        return await self._client.get(f"/order/v1.0/orders/{order_id}")

    async def confirm(self, order_id: str) -> None:
        """Confirma pedido (loja aceitou)."""
        await self._client.post(f"/order/v1.0/orders/{order_id}/confirm")

    async def dispatch(self, order_id: str) -> None:
        """Marca pedido como despachado (saiu pra entrega)."""
        await self._client.post(f"/order/v1.0/orders/{order_id}/dispatch")

    async def request_cancellation(self, order_id: str, reason: str, code: str) -> None:
        """Solicita cancelamento. iFood pode aceitar/recusar.

        Códigos comuns:
          501 - PROBLEMAS_SISTEMA_ESTABELECIMENTO
          502 - PEDIDO_EM_DUPLICIDADE
          503 - ITEM_INDISPONIVEL
          504 - RESTAURANTE_SEM_MOTOBOY
        """
        body = {"reason": reason, "cancellationCode": code}
        await self._client.post(f"/order/v1.0/orders/{order_id}/requestCancellation", json=body)
