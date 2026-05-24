"""Endpoints de pedidos."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gtrifood.api.deps import get_current_tenant, get_db
from gtrifood.api.schemas import CountOut, OrderOut
from gtrifood.models.db import Order

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[OrderOut])
async def list_orders(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    merchant_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Order]:
    stmt = select(Order).where(Order.tenant_id == tenant_id)
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
    merchant_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
) -> CountOut:
    stmt = select(func.count(Order.id)).where(Order.tenant_id == tenant_id)
    if merchant_id:
        stmt = stmt.where(Order.merchant_id == merchant_id)
    if status:
        stmt = stmt.where(Order.status == status)

    result = await db.execute(stmt)
    return CountOut(count=result.scalar_one())


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> Order:
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.tenant_id == tenant_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="pedido não encontrado")
    return order
