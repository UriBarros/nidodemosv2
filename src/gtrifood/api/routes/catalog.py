"""Endpoints do módulo Catalog (cardápio).

- GET   /catalog/categories?client_id&merchant_id
- GET   /catalog/items?client_id&merchant_id&category_id
- PATCH /catalog/items/{id}/status   (body: { status: AVAILABLE|UNAVAILABLE })
- PATCH /catalog/items/{id}/price    (body: { price: 12.50 })
- POST  /catalog/sync?merchant_id    (re-puxa do iFood)
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gtrifood.api.deps import get_current_tenant, get_db
from gtrifood.api.schemas import (
    CatalogCategoryOut,
    CatalogItemOut,
    CatalogItemPriceIn,
    CatalogItemStatusIn,
    CatalogSyncOut,
)
from gtrifood.integrations.ifood.catalog import CatalogAPI
from gtrifood.integrations.ifood.client import IFoodAPIError, IFoodClient
from gtrifood.models.db import CatalogCategory, CatalogItem, Merchant
from gtrifood.services.catalog_sync import sync_catalog_for_merchant

router = APIRouter(prefix="/catalog", tags=["catalog"])


# =============================================================================
# Listar categorias
# =============================================================================
@router.get("/categories", response_model=list[CatalogCategoryOut])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    client_id: uuid.UUID | None = Query(default=None),
    merchant_id: uuid.UUID | None = Query(default=None),
) -> list[CatalogCategory]:
    stmt = select(CatalogCategory).where(CatalogCategory.tenant_id == tenant_id)
    if client_id:
        stmt = stmt.join(
            Merchant, CatalogCategory.merchant_id == Merchant.id
        ).where(Merchant.client_id == client_id)
    if merchant_id:
        stmt = stmt.where(CatalogCategory.merchant_id == merchant_id)
    stmt = stmt.order_by(CatalogCategory.sequence, CatalogCategory.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# =============================================================================
# Listar items
# =============================================================================
@router.get("/items", response_model=list[CatalogItemOut])
async def list_items(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    client_id: uuid.UUID | None = Query(default=None),
    merchant_id: uuid.UUID | None = Query(default=None),
    category_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
) -> list[CatalogItem]:
    stmt = select(CatalogItem).where(CatalogItem.tenant_id == tenant_id)
    if client_id:
        stmt = stmt.join(Merchant, CatalogItem.merchant_id == Merchant.id).where(
            Merchant.client_id == client_id
        )
    if merchant_id:
        stmt = stmt.where(CatalogItem.merchant_id == merchant_id)
    if category_id:
        stmt = stmt.where(CatalogItem.category_id == category_id)
    if status:
        stmt = stmt.where(CatalogItem.status == status.upper())
    stmt = stmt.order_by(CatalogItem.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# =============================================================================
# Atualizar status de item (propaga pro iFood + atualiza local)
# =============================================================================
@router.patch("/items/{item_id}/status", response_model=CatalogItemOut)
async def update_item_status(
    item_id: uuid.UUID,
    payload: CatalogItemStatusIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> CatalogItem:
    new_status = payload.status.upper()
    if new_status not in ("AVAILABLE", "UNAVAILABLE"):
        raise HTTPException(400, "status deve ser AVAILABLE ou UNAVAILABLE")

    item = await _get_item_or_404(db, tenant_id, item_id)
    merchant_info = await _get_merchant_for_item(db, item)

    ifood = await _ifood_for_merchant(merchant_info)
    api = CatalogAPI(ifood)

    try:
        await api.update_item_status(
            merchant_info["ifood_merchant_id"], item.ifood_item_id, new_status
        )
    except IFoodAPIError as e:
        raise HTTPException(
            502, f"iFood rejeitou update de status: {e.body}"
        ) from e

    item.status = new_status
    await db.commit()
    await db.refresh(item)
    return item


# =============================================================================
# Atualizar preço de item
# =============================================================================
@router.patch("/items/{item_id}/price", response_model=CatalogItemOut)
async def update_item_price(
    item_id: uuid.UUID,
    payload: CatalogItemPriceIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> CatalogItem:
    new_price = float(payload.price)
    if new_price < 0:
        raise HTTPException(400, "preço não pode ser negativo")

    item = await _get_item_or_404(db, tenant_id, item_id)
    merchant_info = await _get_merchant_for_item(db, item)

    ifood = await _ifood_for_merchant(merchant_info)
    api = CatalogAPI(ifood)

    try:
        await api.update_item_price(
            merchant_info["ifood_merchant_id"], item.ifood_item_id, new_price
        )
    except IFoodAPIError as e:
        raise HTTPException(
            502, f"iFood rejeitou update de preço: {e.body}"
        ) from e

    item.price = payload.price
    await db.commit()
    await db.refresh(item)
    return item


# =============================================================================
# Sincronizar catalog
# =============================================================================
@router.post("/sync", response_model=CatalogSyncOut)
async def trigger_catalog_sync(
    merchant_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> CatalogSyncOut:
    """Re-puxa todo o cardápio do iFood pra atualizar local."""
    counts = await sync_catalog_for_merchant(merchant_id)
    return CatalogSyncOut(
        merchant_id=merchant_id,
        categories=counts["categories"],
        items=counts["items"],
    )


# =============================================================================
# Helpers
# =============================================================================
async def _get_item_or_404(
    db: AsyncSession, tenant_id: uuid.UUID, item_id: uuid.UUID
) -> CatalogItem:
    result = await db.execute(
        select(CatalogItem).where(
            CatalogItem.id == item_id, CatalogItem.tenant_id == tenant_id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "item não encontrado")
    return item


async def _get_merchant_for_item(
    db: AsyncSession, item: CatalogItem
) -> dict:
    """Retorna info do merchant + client_id pra escolher token_provider."""
    result = await db.execute(
        select(Merchant.ifood_merchant_id, Merchant.client_id).where(
            Merchant.id == item.merchant_id
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "merchant do item não encontrado")
    return {"ifood_merchant_id": row[0], "client_id": row[1]}


async def _ifood_for_merchant(merchant_info: dict) -> IFoodClient:
    """Cria IFoodClient com token correto (per-client ou client_credentials)."""
    if merchant_info.get("client_id"):
        from gtrifood.services.client_tokens import get_or_refresh_access_token

        client_id = merchant_info["client_id"]

        async def _tp() -> str:
            return await get_or_refresh_access_token(client_id)

        return IFoodClient(token_provider=_tp)
    return IFoodClient()
