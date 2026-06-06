"""Endpoints de merchants."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gtrifood.api.deps import get_current_tenant, get_db
from gtrifood.api.schemas import (
    InterruptionIn,
    MerchantOut,
    OpeningHoursIn,
    SyncResultOut,
)
from gtrifood.integrations.ifood.client import IFoodAPIError, IFoodClient
from gtrifood.integrations.ifood.merchants import MerchantAPI
from gtrifood.models.db import Merchant
from gtrifood.services.merchants_sync import sync_merchants_for_tenant

router = APIRouter(prefix="/merchants", tags=["merchants"])


async def _merchant_or_404(
    db: AsyncSession, tenant_id, merchant_id
) -> Merchant:
    result = await db.execute(
        select(Merchant).where(
            Merchant.id == merchant_id, Merchant.tenant_id == tenant_id
        )
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(404, "merchant não encontrado")
    return m


async def _ifood_for_merchant(merchant: Merchant) -> IFoodClient:
    """Cria IFoodClient com token correto (per-client ou client_credentials)."""
    if merchant.client_id:
        from gtrifood.services.client_tokens import get_or_refresh_access_token

        client_id = merchant.client_id

        async def _tp() -> str:
            return await get_or_refresh_access_token(client_id)

        return IFoodClient(token_provider=_tp)
    return IFoodClient()


@router.get("", response_model=list[MerchantOut])
async def list_merchants(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    client_id: uuid.UUID | None = Query(default=None),
) -> list[Merchant]:
    stmt = select(Merchant).where(Merchant.tenant_id == tenant_id)
    if client_id:
        stmt = stmt.where(Merchant.client_id == client_id)
    stmt = stmt.order_by(Merchant.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{merchant_id}", response_model=MerchantOut)
async def get_merchant(
    merchant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> Merchant:
    result = await db.execute(
        select(Merchant).where(
            Merchant.id == merchant_id, Merchant.tenant_id == tenant_id
        )
    )
    merchant = result.scalar_one_or_none()
    if not merchant:
        raise HTTPException(status_code=404, detail="merchant não encontrado")
    return merchant


@router.post("/sync", response_model=SyncResultOut)
async def trigger_sync(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> SyncResultOut:
    count = await sync_merchants_for_tenant(tenant_id)
    return SyncResultOut(inserted=count, message=f"{count} merchant(s) sincronizado(s)")


# =============================================================================
# Disponibilidade / Status
# =============================================================================
@router.get("/{merchant_id}/status")
async def get_merchant_status(
    merchant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> list[dict]:
    m = await _merchant_or_404(db, tenant_id, merchant_id)
    api = MerchantAPI(await _ifood_for_merchant(m))
    try:
        return await api.get_status(m.ifood_merchant_id)
    except IFoodAPIError as e:
        raise HTTPException(502, f"iFood: {e.body}") from e


# =============================================================================
# Interrupções (pausas)
# =============================================================================
@router.get("/{merchant_id}/interruptions")
async def list_interruptions(
    merchant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> list[dict]:
    m = await _merchant_or_404(db, tenant_id, merchant_id)
    api = MerchantAPI(await _ifood_for_merchant(m))
    try:
        return await api.list_interruptions(m.ifood_merchant_id)
    except IFoodAPIError as e:
        raise HTTPException(502, f"iFood: {e.body}") from e


@router.post("/{merchant_id}/interruptions", status_code=201)
async def create_interruption(
    merchant_id: uuid.UUID,
    payload: InterruptionIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict:
    if not payload.description.strip():
        raise HTTPException(400, "descrição obrigatória")
    if payload.end <= payload.start:
        raise HTTPException(400, "end deve ser maior que start")

    m = await _merchant_or_404(db, tenant_id, merchant_id)
    api = MerchantAPI(await _ifood_for_merchant(m))
    try:
        result = await api.create_interruption(
            m.ifood_merchant_id,
            description=payload.description.strip(),
            start=payload.start.isoformat(),
            end=payload.end.isoformat(),
        )
    except IFoodAPIError as e:
        raise HTTPException(
            status_code=400 if 400 <= e.status_code < 500 else 502,
            detail=f"iFood: {e.body}",
        ) from e
    return result or {"status": "created"}


@router.delete("/{merchant_id}/interruptions/{interruption_id}", status_code=204)
async def delete_interruption(
    merchant_id: uuid.UUID,
    interruption_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> None:
    m = await _merchant_or_404(db, tenant_id, merchant_id)
    api = MerchantAPI(await _ifood_for_merchant(m))
    try:
        await api.delete_interruption(m.ifood_merchant_id, interruption_id)
    except IFoodAPIError as e:
        raise HTTPException(
            status_code=400 if 400 <= e.status_code < 500 else 502,
            detail=f"iFood: {e.body}",
        ) from e


# =============================================================================
# Horário de funcionamento
# =============================================================================
@router.get("/{merchant_id}/opening-hours")
async def get_opening_hours(
    merchant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict:
    m = await _merchant_or_404(db, tenant_id, merchant_id)
    api = MerchantAPI(await _ifood_for_merchant(m))
    try:
        return await api.get_opening_hours(m.ifood_merchant_id)
    except IFoodAPIError as e:
        raise HTTPException(502, f"iFood: {e.body}") from e


@router.put("/{merchant_id}/opening-hours")
async def update_opening_hours(
    merchant_id: uuid.UUID,
    payload: OpeningHoursIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict:
    if not payload.shifts:
        raise HTTPException(400, "ao menos 1 shift é obrigatório")

    m = await _merchant_or_404(db, tenant_id, merchant_id)
    api = MerchantAPI(await _ifood_for_merchant(m))
    shifts_dicts = [s.model_dump() for s in payload.shifts]
    try:
        result = await api.update_opening_hours(m.ifood_merchant_id, shifts_dicts)
    except IFoodAPIError as e:
        raise HTTPException(
            status_code=400 if 400 <= e.status_code < 500 else 502,
            detail=f"iFood: {e.body}",
        ) from e
    return result or {"status": "updated", "shifts": shifts_dicts}
