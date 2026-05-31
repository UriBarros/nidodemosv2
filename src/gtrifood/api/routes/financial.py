"""Endpoints financeiros."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gtrifood.api.deps import get_current_tenant, get_db
from gtrifood.api.schemas import FinancialEventOut, SyncResultOut
from gtrifood.models.db import FinancialEvent, Merchant
from gtrifood.services.financial_sync import sync_financial_for_merchant

router = APIRouter(prefix="/financial", tags=["financial"])


@router.get("", response_model=list[FinancialEventOut])
async def list_financial(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    client_id: uuid.UUID | None = Query(default=None),
    merchant_id: uuid.UUID | None = Query(default=None),
    event_type: str | None = Query(default=None),
    begin: date | None = Query(default=None),
    end: date | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[FinancialEvent]:
    stmt = select(FinancialEvent).where(FinancialEvent.tenant_id == tenant_id)
    if client_id:
        stmt = stmt.join(Merchant, FinancialEvent.merchant_id == Merchant.id).where(
            Merchant.client_id == client_id
        )
    if merchant_id:
        stmt = stmt.where(FinancialEvent.merchant_id == merchant_id)
    if event_type:
        stmt = stmt.where(FinancialEvent.event_type == event_type)
    if begin:
        stmt = stmt.where(FinancialEvent.competence_date >= begin)
    if end:
        stmt = stmt.where(FinancialEvent.competence_date <= end)
    stmt = stmt.order_by(desc(FinancialEvent.competence_date)).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/summary")
async def financial_summary(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    client_id: uuid.UUID | None = Query(default=None),
    merchant_id: uuid.UUID | None = Query(default=None),
) -> dict[str, float]:
    """Soma agregada por tipo de evento."""
    stmt = select(FinancialEvent.event_type, func.sum(FinancialEvent.amount)).where(
        FinancialEvent.tenant_id == tenant_id
    )
    if client_id:
        stmt = stmt.join(Merchant, FinancialEvent.merchant_id == Merchant.id).where(
            Merchant.client_id == client_id
        )
    if merchant_id:
        stmt = stmt.where(FinancialEvent.merchant_id == merchant_id)
    stmt = stmt.group_by(FinancialEvent.event_type)

    result = await db.execute(stmt)
    return {row[0]: float(row[1] or 0) for row in result.all()}


@router.post("/sync", response_model=SyncResultOut)
async def trigger_financial_sync(
    merchant_id: uuid.UUID,
    days_back: int = Query(default=30, ge=1, le=365),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> SyncResultOut:
    try:
        count = await sync_financial_for_merchant(
            tenant_id, merchant_id, days_back=days_back
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return SyncResultOut(inserted=count, message=f"{count} evento(s) financeiro(s) sincronizado(s)")
