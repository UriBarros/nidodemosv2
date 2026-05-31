"""Endpoints de merchants."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gtrifood.api.deps import get_current_tenant, get_db
from gtrifood.api.schemas import MerchantOut, SyncResultOut
from gtrifood.models.db import Merchant
from gtrifood.services.merchants_sync import sync_merchants_for_tenant

router = APIRouter(prefix="/merchants", tags=["merchants"])


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
