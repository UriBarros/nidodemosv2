"""Endpoints de merchants."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gtrifood.api.deps import get_db, get_tenant_id
from gtrifood.api.schemas import MerchantOut, SyncResultOut
from gtrifood.models.db import Merchant
from gtrifood.services.merchants_sync import sync_merchants_for_tenant

router = APIRouter(prefix="/merchants", tags=["merchants"])


@router.get("", response_model=list[MerchantOut])
async def list_merchants(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> list[Merchant]:
    result = await db.execute(
        select(Merchant)
        .where(Merchant.tenant_id == tenant_id)
        .order_by(Merchant.name)
    )
    return list(result.scalars().all())


@router.get("/{merchant_id}", response_model=MerchantOut)
async def get_merchant(
    merchant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
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
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> SyncResultOut:
    count = await sync_merchants_for_tenant(tenant_id)
    return SyncResultOut(inserted=count, message=f"{count} merchant(s) sincronizado(s)")
