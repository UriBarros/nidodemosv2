"""Endpoints de pedidos."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gtrifood.api.deps import get_current_tenant, get_db
from gtrifood.api.schemas import CountOut, OrderDetailOut, OrderEventOut, OrderOut
from gtrifood.integrations.ifood.client import IFoodAPIError, IFoodClient
from gtrifood.integrations.ifood.orders import OrdersAPI
from gtrifood.models.db import Merchant, Order, OrderEvent

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[OrderOut])
async def list_orders(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    client_id: uuid.UUID | None = Query(default=None),
    merchant_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Order]:
    stmt = select(Order).where(Order.tenant_id == tenant_id)
    if client_id:
        stmt = stmt.join(Merchant, Order.merchant_id == Merchant.id).where(
            Merchant.client_id == client_id
        )
    if merchant_id:
        stmt = stmt.where(Order.merchant_id == merchant_id)
    if status:
        stmt = stmt.where(Order.status == status)
    stmt = stmt.order_by(desc(Order.created_at_ifood)).limit(limit).offset(offset)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/count", response_model=CountOut)
async def count_orders(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    client_id: uuid.UUID | None = Query(default=None),
    merchant_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    begin: str | None = Query(default=None, description="ISO datetime/date — created_at_ifood >= begin"),
    end: str | None = Query(default=None, description="ISO datetime/date — created_at_ifood <= end"),
) -> CountOut:
    from datetime import datetime

    stmt = select(func.count(Order.id)).where(Order.tenant_id == tenant_id)
    if client_id:
        stmt = stmt.join(Merchant, Order.merchant_id == Merchant.id).where(
            Merchant.client_id == client_id
        )
    if merchant_id:
        stmt = stmt.where(Order.merchant_id == merchant_id)
    if status:
        stmt = stmt.where(Order.status == status)

    # Parse begin/end pra datetime — aceita ISO 8601 (com ou sem Z)
    if begin:
        try:
            dt = datetime.fromisoformat(begin.replace("Z", "+00:00"))
            stmt = stmt.where(Order.created_at_ifood >= dt)
        except ValueError as e:
            raise HTTPException(400, f"begin inválido: {e}") from e
    if end:
        try:
            dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            stmt = stmt.where(Order.created_at_ifood <= dt)
        except ValueError as e:
            raise HTTPException(400, f"end inválido: {e}") from e

    try:
        result = await db.execute(stmt)
        return CountOut(count=result.scalar_one())
    except Exception as e:
        raise HTTPException(500, f"erro na query: {type(e).__name__}: {e}") from e


@router.get("/{order_id}", response_model=OrderDetailOut)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> Order:
    """Retorna pedido com raw_data completo (todos os campos iFood)."""
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.tenant_id == tenant_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="pedido não encontrado")
    return order


async def _get_order_or_404(
    order_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession
) -> Order:
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.tenant_id == tenant_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="pedido não encontrado")
    return order


@router.post("/{order_id}/confirm", status_code=202)
async def confirm_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict[str, str]:
    """Confirma pedido (loja aceita). iFood emite evento CFM em seguida."""
    order = await _get_order_or_404(order_id, tenant_id, db)
    api = OrdersAPI(IFoodClient())
    try:
        await api.confirm(order.ifood_order_id)
    except IFoodAPIError as e:
        raise HTTPException(status_code=502, detail=f"iFood: {e}") from e
    return {"message": "Pedido confirmado. Aguarde evento CFM."}


@router.post("/{order_id}/dispatch", status_code=202)
async def dispatch_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict[str, str]:
    """Marca pedido como despachado (saiu pra entrega)."""
    order = await _get_order_or_404(order_id, tenant_id, db)
    api = OrdersAPI(IFoodClient())
    try:
        await api.dispatch(order.ifood_order_id)
    except IFoodAPIError as e:
        raise HTTPException(status_code=502, detail=f"iFood: {e}") from e
    return {"message": "Pedido despachado. Aguarde evento DSP."}


@router.post("/{order_id}/ready-to-pickup", status_code=202)
async def ready_to_pickup_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict[str, str]:
    """Marca pedido como pronto pra retirada (RPR)."""
    order = await _get_order_or_404(order_id, tenant_id, db)
    api = OrdersAPI(IFoodClient())
    try:
        await api.ready_to_pickup(order.ifood_order_id)
    except IFoodAPIError as e:
        raise HTTPException(status_code=502, detail=f"iFood: {e}") from e
    return {"message": "Pedido pronto pra retirada. Aguarde evento RPR."}


@router.post("/{order_id}/cancel", status_code=202)
async def cancel_order(
    order_id: uuid.UUID,
    reason: str = Query(..., min_length=3),
    code: str = Query(
        "501",
        description="Código iFood: 501=PROBLEMAS_SISTEMA, 502=DUPLICIDADE, "
        "503=ITEM_INDISPONIVEL, 504=SEM_MOTOBOY",
    ),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict[str, str]:
    """Solicita cancelamento. iFood pode aceitar (CRA) ou recusar (CRD)."""
    order = await _get_order_or_404(order_id, tenant_id, db)
    api = OrdersAPI(IFoodClient())
    try:
        await api.request_cancellation(order.ifood_order_id, reason=reason, code=code)
    except IFoodAPIError as e:
        raise HTTPException(status_code=502, detail=f"iFood: {e}") from e
    return {"message": "Cancelamento solicitado. Aguarde evento CRA ou CRD."}


@router.get("/{order_id}/events", response_model=list[OrderEventOut])
async def get_order_events(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> list[OrderEvent]:
    """Timeline de eventos do pedido (PLC → CFM → DSP → CON ou cancelamentos)."""
    order_result = await db.execute(
        select(Order).where(Order.id == order_id, Order.tenant_id == tenant_id)
    )
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="pedido não encontrado")

    events_result = await db.execute(
        select(OrderEvent)
        .where(
            OrderEvent.tenant_id == tenant_id,
            OrderEvent.ifood_order_id == order.ifood_order_id,
        )
        .order_by(OrderEvent.received_at)
    )
    return list(events_result.scalars().all())
