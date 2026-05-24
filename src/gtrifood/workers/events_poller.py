"""Worker de polling de eventos iFood.

Loop:
1. GET /events:polling
2. Pra cada evento:
   - Persiste em order_events (auditoria)
   - Se for evento de pedido (PLC, CFM, DSP, CON, CAN, etc) → fetch + upsert order
3. POST /events/acknowledgment com IDs processados
4. Sleep 30s

Roda contínuo. Encerra graciosamente com SIGINT.
"""

from __future__ import annotations

import asyncio
import signal
import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from gtrifood.core.db import get_session
from gtrifood.core.logging import configure_logging, get_logger
from gtrifood.integrations.ifood.client import IFoodClient
from gtrifood.integrations.ifood.events import EventsAPI
from gtrifood.models.db import Merchant, OrderEvent
from gtrifood.services.orders_sync import upsert_order

POLL_INTERVAL_SECONDS = 30

# Categorias que ignoramos (heartbeat, controle interno)
IGNORED_CATEGORIES = {"KEEPALIVE", "HANDSHAKE"}

# Códigos conhecidos de status de pedido (referência — não restringimos por
# essa lista; qualquer evento ORDER_STATUS com orderId é processado).
# PLC=PLACED, CFM=CONFIRMED, RPR=READY_FOR_PICKUP, DSP=DISPATCHED,
# ARR=ARRIVED, CON=CONCLUDED, CAN=CANCELLED, CAR=CANCELLATION_REQUESTED,
# CRA=CANCELLATION_REQUEST_ACCEPTED, CRD=CANCELLATION_REQUEST_DENIED.


class EventsPoller:
    def __init__(self) -> None:
        self._client = IFoodClient()
        self._api = EventsAPI(self._client)
        self._log = get_logger("events_poller")
        self._stopping = False

    def stop(self) -> None:
        self._stopping = True

    async def _resolve_merchant(self, ifood_merchant_id: str) -> tuple[uuid.UUID, uuid.UUID] | None:
        """Acha (tenant_id, merchant_id) interno a partir do ifood_merchant_id."""
        async with get_session() as session:
            result = await session.execute(
                select(Merchant.tenant_id, Merchant.id).where(
                    Merchant.ifood_merchant_id == ifood_merchant_id
                )
            )
            row = result.first()
            return (row[0], row[1]) if row else None

    async def _persist_event(self, event: dict[str, Any]) -> None:
        """Salva evento bruto em order_events (idempotente por ifood_event_id)."""
        ifood_merchant_id = event.get("merchantId") or event.get("merchant", {}).get("id")
        resolved = await self._resolve_merchant(ifood_merchant_id) if ifood_merchant_id else None

        stmt = insert(OrderEvent).values(
            tenant_id=resolved[0] if resolved else None,
            merchant_id=resolved[1] if resolved else None,
            ifood_event_id=event["id"],
            ifood_order_id=event.get("orderId"),
            code=event.get("code") or "UNKNOWN",
            full_code=event.get("fullCode"),
            payload=event,
        )
        # se já existe (reentrega antes do ack), ignora
        stmt = stmt.on_conflict_do_nothing(index_elements=["ifood_event_id"])

        async with get_session() as session:
            await session.execute(stmt)

    async def _process_event(self, event: dict[str, Any]) -> None:
        """Persiste evento + se for ORDER_STATUS, sincroniza order.

        Não hardcoda lista de códigos. Confia no `category` do iFood:
        - ORDER_STATUS: muda status do pedido — busca detalhes + UPSERT
        - KEEPALIVE/HANDSHAKE: ignora (sem persistir)
        - SAC, outros: persiste pra auditoria mas não atualiza order
        """
        category = (event.get("category") or "ORDER_STATUS").upper()

        # Heartbeats não precisam ser auditados — só polui order_events
        if category in IGNORED_CATEGORIES:
            return

        await self._persist_event(event)

        code = event.get("code")
        full_code = event.get("fullCode")
        order_id = event.get("orderId")
        ifood_merchant_id = event.get("merchantId") or event.get("merchant", {}).get("id")

        # Só ORDER_STATUS gera UPSERT em orders
        if category != "ORDER_STATUS" or not order_id or not ifood_merchant_id:
            self._log.debug(
                "evento_sem_acao_order",
                category=category,
                code=code,
                order_id=order_id,
            )
            return

        resolved = await self._resolve_merchant(ifood_merchant_id)
        if not resolved:
            self._log.warning("merchant_desconhecido", ifood_merchant_id=ifood_merchant_id)
            return

        try:
            await upsert_order(
                resolved[0],
                resolved[1],
                order_id,
                status=full_code or code,
            )
            self._log.info(
                "order_status_processado",
                ifood_order_id=order_id,
                code=code,
                full_code=full_code,
            )
        except Exception as e:
            self._log.error(
                "falha_upsert_order",
                ifood_order_id=order_id,
                code=code,
                error=str(e),
            )

    async def run_once(self) -> int:
        """Faz uma iteração: poll → process → ack. Retorna número de eventos processados."""
        events = await self._api.poll()
        if not events:
            return 0

        self._log.info("eventos_recebidos", count=len(events))
        processed_ids: list[str] = []
        for ev in events:
            try:
                await self._process_event(ev)
                processed_ids.append(ev["id"])
            except Exception as e:
                self._log.error("falha_processar_evento", event_id=ev.get("id"), error=str(e))

        if processed_ids:
            try:
                await self._api.acknowledge(processed_ids)
                # marca acknowledged_at no banco
                async with get_session() as session:
                    await session.execute(
                        update(OrderEvent)
                        .where(OrderEvent.ifood_event_id.in_(processed_ids))
                        .values(acknowledged_at=func.now())
                    )
                self._log.info("eventos_ack", count=len(processed_ids))
            except Exception as e:
                self._log.error("falha_ack", error=str(e), ids=processed_ids)

        return len(processed_ids)

    async def run_forever(self) -> None:
        self._log.info("worker_iniciado", interval_seconds=POLL_INTERVAL_SECONDS)
        while not self._stopping:
            try:
                await self.run_once()
            except Exception as e:
                self._log.error("erro_iteracao", error=str(e))
            # sleep responsivo a SIGINT
            for _ in range(POLL_INTERVAL_SECONDS):
                if self._stopping:
                    break
                await asyncio.sleep(1)
        self._log.info("worker_parado")


async def main() -> None:
    configure_logging()
    poller = EventsPoller()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, poller.stop)
        except NotImplementedError:
            # Windows: signal handlers limitados; SIGINT via KeyboardInterrupt já funciona
            pass

    try:
        await poller.run_forever()
    except KeyboardInterrupt:
        poller.stop()


if __name__ == "__main__":
    from gtrifood.core.asyncio_compat import setup_event_loop

    setup_event_loop()
    asyncio.run(main())
