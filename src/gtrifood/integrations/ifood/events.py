"""Polling de eventos da API iFood + acknowledgment.

Fluxo correto:
1. GET /events/v1.0/events:polling → recebe array de eventos
2. Processa cada evento (persiste, despacha pra service correspondente)
3. POST /events/v1.0/events/acknowledgment com IDs processados
   → sem ack, iFood reenvia indefinidamente

Recomendação iFood: polling a cada 30s no mínimo.
"""

from __future__ import annotations

from typing import Any

from gtrifood.integrations.ifood.client import IFoodClient


class EventsAPI:
    def __init__(self, client: IFoodClient) -> None:
        self._client = client

    async def poll(self) -> list[dict[str, Any]]:
        """Busca eventos novos. Retorna lista vazia se nada novo."""
        result = await self._client.get("/events/v1.0/events:polling")
        return result or []

    async def acknowledge(self, event_ids: list[str]) -> None:
        """Confirma processamento dos eventos. iFood não reenvia mais.

        Body: [{"id": "<eventId>"}, ...]
        """
        if not event_ids:
            return
        body = [{"id": eid} for eid in event_ids]
        await self._client.post("/events/v1.0/events/acknowledgment", json=body)
