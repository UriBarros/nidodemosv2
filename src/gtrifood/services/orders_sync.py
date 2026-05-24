"""Sincronização de pedidos.

Fluxo: dado um order_id (vindo de um evento), busca detalhes no iFood e UPSERT.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert

from gtrifood.core.db import get_session
from gtrifood.core.logging import get_logger
from gtrifood.integrations.ifood.client import IFoodClient
from gtrifood.integrations.ifood.orders import OrdersAPI
from gtrifood.models.db import Order

logger = get_logger(__name__)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _safe_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return None


async def upsert_order(
    tenant_id: uuid.UUID,
    merchant_id: uuid.UUID,
    ifood_order_id: str,
    *,
    status: str | None = None,
) -> None:
    """Busca pedido no iFood e UPSERT na tabela orders.

    Args:
        status: status vindo do evento (ex: 'PLACED', 'CONFIRMED'). Tem prioridade
                sobre `raw['status']` porque o GET /orders/{id} nem sempre traz status.
    """
    api = OrdersAPI(IFoodClient())
    raw = await api.get_order(ifood_order_id)

    customer = raw.get("customer") or {}
    total = (raw.get("total") or {}).get("orderAmount")

    resolved_status = status or raw.get("status") or "UNKNOWN"

    stmt = insert(Order).values(
        tenant_id=tenant_id,
        merchant_id=merchant_id,
        ifood_order_id=ifood_order_id,
        display_id=raw.get("displayId"),
        status=resolved_status,
        order_type=raw.get("orderType"),
        created_at_ifood=_parse_dt(raw.get("createdAt")),
        total_amount=_safe_decimal(total),
        customer_name=customer.get("name"),
        raw_data=raw,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["tenant_id", "ifood_order_id"],
        set_={
            "status": stmt.excluded.status,
            "display_id": stmt.excluded.display_id,
            "order_type": stmt.excluded.order_type,
            "total_amount": stmt.excluded.total_amount,
            "customer_name": stmt.excluded.customer_name,
            "raw_data": stmt.excluded.raw_data,
        },
    )

    async with get_session() as session:
        await session.execute(stmt)

    logger.info(
        "pedido_persistido",
        ifood_order_id=ifood_order_id,
        status=resolved_status,
        merchant_id=str(merchant_id),
    )
