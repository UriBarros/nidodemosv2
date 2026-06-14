"""Endpoints financeiros."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gtrifood.api.deps import get_current_tenant, get_db
from gtrifood.api.schemas import FinancialEventOut, SyncResultOut
from gtrifood.integrations.ifood.client import IFoodAPIError, IFoodClient
from gtrifood.integrations.ifood.financial import FinancialAPI
from gtrifood.models.db import FinancialEvent, Merchant
from gtrifood.services.financial_sync import sync_financial_for_merchant

router = APIRouter(prefix="/financial", tags=["financial"])


async def _ifood_for_merchant(
    db: AsyncSession, tenant_id: uuid.UUID, merchant_id: uuid.UUID
) -> tuple[str, IFoodClient]:
    """Resolve merchant local id -> (ifood_merchant_id, client pronto)."""
    row = await db.execute(
        select(Merchant.ifood_merchant_id, Merchant.client_id).where(
            Merchant.id == merchant_id, Merchant.tenant_id == tenant_id
        )
    )
    rec = row.first()
    if not rec:
        raise HTTPException(404, "merchant não encontrado")
    ifood_merchant_id, client_id = rec
    if client_id:
        from gtrifood.services.client_tokens import get_or_refresh_access_token

        async def _tp() -> str:
            return await get_or_refresh_access_token(client_id)

        return ifood_merchant_id, IFoodClient(token_provider=_tp)
    return ifood_merchant_id, IFoodClient()


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
    begin: date | None = Query(default=None),
    end: date | None = Query(default=None),
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
    if begin:
        stmt = stmt.where(FinancialEvent.competence_date >= begin)
    if end:
        stmt = stmt.where(FinancialEvent.competence_date <= end)
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


# =============================================================================
# Pass-through pra Financial v3.0 (consultas live, sem persistir)
# =============================================================================
@router.get("/reconciliation")
async def get_reconciliation_live(
    merchant_id: uuid.UUID,
    begin: date,
    end: date,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict | list:
    """Conciliação consolidada do período (live via Financial v3.0)."""
    ifood_id, ifood = await _ifood_for_merchant(db, tenant_id, merchant_id)
    api = FinancialAPI(ifood)
    try:
        return await api.get_reconciliation(ifood_id, begin, end)
    except IFoodAPIError as e:
        raise HTTPException(502, f"iFood: {e.body}") from e


@router.get("/settlements")
async def list_settlements_live(
    merchant_id: uuid.UUID,
    begin: date,
    end: date,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> list[dict]:
    """Repasses pagos no período (live)."""
    ifood_id, ifood = await _ifood_for_merchant(db, tenant_id, merchant_id)
    api = FinancialAPI(ifood)
    try:
        return await api.list_settlements(ifood_id, begin, end)
    except IFoodAPIError as e:
        raise HTTPException(502, f"iFood: {e.body}") from e


@router.post("/reconciliation/on-demand", status_code=202)
async def request_reconciliation_on_demand(
    merchant_id: uuid.UUID,
    begin: date,
    end: date,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict:
    """Agenda geração de arquivo de conciliação. Retorna {requestId: ...}."""
    ifood_id, ifood = await _ifood_for_merchant(db, tenant_id, merchant_id)
    api = FinancialAPI(ifood)
    try:
        result = await api.request_reconciliation_on_demand(ifood_id, begin, end)
    except IFoodAPIError as e:
        raise HTTPException(502, f"iFood: {e.body}") from e
    return result or {"status": "requested"}


@router.get("/reconciliation/on-demand/{request_id}")
async def fetch_reconciliation_file(
    request_id: str,
    merchant_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict:
    """Busca metadados/URL do arquivo de conciliação gerado."""
    ifood_id, ifood = await _ifood_for_merchant(db, tenant_id, merchant_id)
    api = FinancialAPI(ifood)
    try:
        return await api.fetch_reconciliation_file(ifood_id, request_id)
    except IFoodAPIError as e:
        raise HTTPException(502, f"iFood: {e.body}") from e
