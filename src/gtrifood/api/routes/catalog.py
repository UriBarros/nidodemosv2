"""Endpoints do módulo Catalog (cardápio).

- GET   /catalog/categories?client_id&merchant_id
- GET   /catalog/items?client_id&merchant_id&category_id
- PATCH /catalog/items/{id}/status   (body: { status: AVAILABLE|UNAVAILABLE })
- PATCH /catalog/items/{id}/price    (body: { price: 12.50 })
- POST  /catalog/sync?merchant_id    (re-puxa do iFood)
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gtrifood.api.deps import get_current_tenant, get_db
from gtrifood.api.schemas import (
    CatalogCategoryOut,
    CatalogItemOut,
    CatalogItemPriceIn,
    CatalogItemStatusIn,
    CatalogSyncOut,
    CategoryCreateIn,
    ItemCreateIn,
    ItemUpdateIn,
    OptionCreateIn,
    OptionGroupCreateIn,
    OptionUpdateIn,
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


async def _merchant_ctx(
    db: AsyncSession, tenant_id: uuid.UUID, merchant_id: uuid.UUID
) -> tuple[Merchant, dict, IFoodClient]:
    """Retorna merchant + dict info + IFoodClient pronto pra usar."""
    result = await db.execute(
        select(Merchant).where(
            Merchant.id == merchant_id, Merchant.tenant_id == tenant_id
        )
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(404, "merchant não encontrado")
    info = {"ifood_merchant_id": m.ifood_merchant_id, "client_id": m.client_id}
    return m, info, await _ifood_for_merchant(info)


# =============================================================================
# Criar categoria
# =============================================================================
@router.post("/categories", status_code=201)
async def create_category(
    payload: CategoryCreateIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict:
    if not payload.name.strip():
        raise HTTPException(400, "nome obrigatório")
    _, info, ifood = await _merchant_ctx(db, tenant_id, payload.merchant_id)
    api = CatalogAPI(ifood)

    catalogs = await api.list_catalogs(info["ifood_merchant_id"])
    if not catalogs:
        raise HTTPException(400, "merchant sem catálogo iFood")
    catalog_id = catalogs[0].get("catalogId") or catalogs[0].get("id")

    try:
        result = await api.create_category(
            info["ifood_merchant_id"],
            catalog_id,
            name=payload.name.strip(),
            external_code=payload.external_code,
        )
    except IFoodAPIError as e:
        raise HTTPException(
            status_code=400 if 400 <= e.status_code < 500 else 502,
            detail=f"iFood: {e.body}",
        ) from e
    return result or {"status": "created"}


# =============================================================================
# Criar / atualizar item completo (PUT /items com optionGroups inline)
# =============================================================================
@router.post("/items/full", status_code=201)
async def upsert_item_full(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict:
    """Cria ou atualiza item completo via PUT /items.

    Body esperado:
    {
      "merchant_id": "<uuid local>",
      "category_id": "<uuid local>" (resolvido pra ifood_category_id),
      "item": { ...payload iFood completo com product/price/optionGroups... }
    }
    """
    merchant_id = payload.get("merchant_id")
    category_local_id = payload.get("category_id")
    item_payload = payload.get("item")
    if not (merchant_id and category_local_id and isinstance(item_payload, dict)):
        raise HTTPException(
            400,
            "payload requer merchant_id, category_id e item (dict)",
        )

    try:
        merchant_uuid = uuid.UUID(str(merchant_id))
        category_uuid = uuid.UUID(str(category_local_id))
    except ValueError as e:
        raise HTTPException(400, f"id inválido: {e}") from e

    cat_row = await db.execute(
        select(CatalogCategory.ifood_category_id).where(
            CatalogCategory.id == category_uuid,
            CatalogCategory.tenant_id == tenant_id,
        )
    )
    ifood_cat = cat_row.scalar_one_or_none()
    if not ifood_cat:
        raise HTTPException(404, "categoria não encontrada")

    _, info, ifood = await _merchant_ctx(db, tenant_id, merchant_uuid)
    api = CatalogAPI(ifood)

    try:
        result = await api.upsert_item(
            info["ifood_merchant_id"],
            category_id=ifood_cat,
            item=item_payload,
        )
    except IFoodAPIError as e:
        raise HTTPException(
            status_code=400 if 400 <= e.status_code < 500 else 502,
            detail=f"iFood: {e.body}",
        ) from e
    return result or {"status": "upserted"}


# =============================================================================
# Criar item (atalho com payload mínimo — chama PUT /items sob o capô)
# =============================================================================
@router.post("/items", status_code=201)
async def create_item(
    payload: ItemCreateIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict:
    if not payload.name.strip():
        raise HTTPException(400, "nome obrigatório")
    if payload.price < 0:
        raise HTTPException(400, "preço não pode ser negativo")

    # Resolve category_id → ifood_category_id
    cat_row = await db.execute(
        select(CatalogCategory.ifood_category_id).where(
            CatalogCategory.id == payload.category_id,
            CatalogCategory.tenant_id == tenant_id,
        )
    )
    ifood_cat = cat_row.scalar_one_or_none()
    if not ifood_cat:
        raise HTTPException(404, "categoria não encontrada")

    _, info, ifood = await _merchant_ctx(db, tenant_id, payload.merchant_id)
    api = CatalogAPI(ifood)

    try:
        result = await api.create_item(
            info["ifood_merchant_id"],
            category_id=ifood_cat,
            name=payload.name.strip(),
            description=payload.description,
            price=float(payload.price),
            status=payload.status,
            external_code=payload.external_code,
            image_path=payload.image_path,
        )
    except IFoodAPIError as e:
        raise HTTPException(
            status_code=400 if 400 <= e.status_code < 500 else 502,
            detail=f"iFood: {e.body}",
        ) from e
    return result or {"status": "created"}


# =============================================================================
# Atualizar item (nome/descrição/foto)
# =============================================================================
@router.patch("/items/{item_id}", response_model=CatalogItemOut)
async def update_item(
    item_id: uuid.UUID,
    payload: ItemUpdateIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> CatalogItem:
    item = await _get_item_or_404(db, tenant_id, item_id)
    merchant_info = await _get_merchant_for_item(db, item)
    ifood = await _ifood_for_merchant(merchant_info)
    api = CatalogAPI(ifood)

    try:
        await api.update_item(
            merchant_info["ifood_merchant_id"],
            item.ifood_item_id,
            name=payload.name,
            description=payload.description,
            image_path=payload.image_path,
            external_code=payload.external_code,
        )
    except IFoodAPIError as e:
        raise HTTPException(
            status_code=400 if 400 <= e.status_code < 500 else 502,
            detail=f"iFood: {e.body}",
        ) from e

    # Atualiza local
    if payload.name is not None:
        item.name = payload.name
    if payload.description is not None:
        item.description = payload.description
    if payload.image_path is not None:
        item.image_path = payload.image_path
    if payload.external_code is not None:
        item.external_code = payload.external_code
    await db.commit()
    await db.refresh(item)
    return item


# =============================================================================
# Upload de imagem
# =============================================================================
@router.post("/upload-image")
async def upload_image(
    merchant_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict:
    _, info, ifood = await _merchant_ctx(db, tenant_id, merchant_id)
    api = CatalogAPI(ifood)
    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(400, "imagem máx 10MB")
    try:
        result = await api.upload_image(
            info["ifood_merchant_id"],
            image_bytes,
            content_type=file.content_type or "image/jpeg",
        )
    except IFoodAPIError as e:
        raise HTTPException(
            status_code=400 if 400 <= e.status_code < 500 else 502,
            detail=f"iFood: {e.body}",
        ) from e
    return result or {"status": "uploaded"}


# =============================================================================
# Option groups + opções (complementos)
# =============================================================================
@router.get("/option-groups")
async def list_option_groups(
    merchant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> list[dict]:
    _, info, ifood = await _merchant_ctx(db, tenant_id, merchant_id)
    api = CatalogAPI(ifood)
    try:
        return await api.list_option_groups(info["ifood_merchant_id"])
    except IFoodAPIError as e:
        raise HTTPException(502, f"iFood: {e.body}") from e


@router.post("/option-groups", status_code=501)
async def create_option_group(
    payload: OptionGroupCreateIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict:
    """DEPRECATED na Catalog v2.0: não existe POST /optionGroups standalone.

    Grupos nascem dentro de PUT /items com optionGroups + options aninhados.
    Use POST /catalog/option-groups/add-to-item (alto nível) ou POST
    /catalog/items/full enviando o item completo.
    """
    raise HTTPException(
        status_code=501,
        detail=(
            "iFood Catalog v2.0 não suporta criar optionGroup standalone. "
            "Use POST /catalog/option-groups/add-to-item ou POST "
            "/catalog/items/full com optionGroups aninhados."
        ),
    )


@router.post("/option-groups/add-to-item", status_code=201)
async def add_option_group_to_item(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict:
    """Adiciona um grupo de complementos a um item existente.

    Internamente: busca item completo via GET /items/{id}/flat, anexa o novo
    optionGroup com options inline, e re-envia via PUT /items (idempotente).

    Body:
    {
      "merchant_id": "<uuid local>",
      "item_id": "<uuid local do CatalogItem>",
      "name": "Bordas",
      "min": 0,
      "max": 1,
      "options": [
        {"name": "Catupiry", "price": 3.50, "status": "AVAILABLE"},
        ...
      ]
    }
    """
    try:
        merchant_uuid = uuid.UUID(str(payload.get("merchant_id")))
        item_uuid = uuid.UUID(str(payload.get("item_id")))
    except (ValueError, TypeError) as e:
        raise HTTPException(400, f"id inválido: {e}") from e

    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "nome do grupo obrigatório")
    options = payload.get("options") or []
    if not isinstance(options, list):
        raise HTTPException(400, "options deve ser lista")

    item_row = await db.execute(
        select(CatalogItem.ifood_item_id).where(
            CatalogItem.id == item_uuid, CatalogItem.tenant_id == tenant_id
        )
    )
    ifood_item_id = item_row.scalar_one_or_none()
    if not ifood_item_id:
        raise HTTPException(404, "item não encontrado")

    _, info, ifood = await _merchant_ctx(db, tenant_id, merchant_uuid)
    api = CatalogAPI(ifood)

    try:
        flat = await api.get_item_flat(info["ifood_merchant_id"], ifood_item_id)
    except IFoodAPIError as e:
        raise HTTPException(502, f"iFood get_item_flat: {e.body}") from e

    existing_groups = list(flat.get("optionGroups") or [])
    new_options: list[dict] = []
    for op in options:
        if not op.get("name"):
            continue
        try:
            price_val = float(op.get("price") or 0)
        except (TypeError, ValueError):
            raise HTTPException(400, f"preço inválido em {op}")
        new_options.append({
            "product": {"name": str(op["name"]).strip()},
            "price": {"value": price_val},
            "status": op.get("status") or "AVAILABLE",
        })

    existing_groups.append({
        "name": name,
        "min": int(payload.get("min") or 0),
        "max": int(payload.get("max") or 1),
        "status": "AVAILABLE",
        "options": new_options,
    })

    item_payload = {
        **flat,
        "optionGroups": existing_groups,
    }

    try:
        result = await api.upsert_item(
            info["ifood_merchant_id"],
            category_id=flat.get("categoryId") or "",
            item=item_payload,
        )
    except IFoodAPIError as e:
        raise HTTPException(
            status_code=400 if 400 <= e.status_code < 500 else 502,
            detail=f"iFood PUT /items: {e.body}",
        ) from e
    return result or {"status": "created"}


@router.patch("/option-groups/{option_group_id}/status")
async def update_option_group_status(
    option_group_id: str,
    merchant_id: uuid.UUID = Query(...),
    status: str = Query(..., description="AVAILABLE | UNAVAILABLE"),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict:
    """Pausa/ativa um grupo de complementos inteiro."""
    new_status = status.upper()
    if new_status not in ("AVAILABLE", "UNAVAILABLE"):
        raise HTTPException(400, "status deve ser AVAILABLE ou UNAVAILABLE")
    _, info, ifood = await _merchant_ctx(db, tenant_id, merchant_id)
    api = CatalogAPI(ifood)
    try:
        result = await api.update_option_group_status(
            info["ifood_merchant_id"], option_group_id, new_status
        )
    except IFoodAPIError as e:
        raise HTTPException(502, f"iFood: {e.body}") from e
    return result or {"status": "updated"}


@router.post("/options", status_code=201)
async def create_option(
    payload: OptionCreateIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict:
    if not payload.name.strip():
        raise HTTPException(400, "nome obrigatório")
    if payload.price < 0:
        raise HTTPException(400, "preço não pode ser negativo")
    _, info, ifood = await _merchant_ctx(db, tenant_id, payload.merchant_id)
    api = CatalogAPI(ifood)
    try:
        result = await api.create_option(
            info["ifood_merchant_id"],
            option_group_id=payload.option_group_id,
            name=payload.name.strip(),
            price=float(payload.price),
            status=payload.status,
            image_path=payload.image_path,
            external_code=payload.external_code,
        )
    except IFoodAPIError as e:
        raise HTTPException(
            status_code=400 if 400 <= e.status_code < 500 else 502,
            detail=f"iFood: {e.body}",
        ) from e
    return result or {"status": "created"}


@router.patch("/options/{option_id}")
async def update_option(
    option_id: str,  # iFood id
    payload: OptionUpdateIn,
    merchant_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict:
    _, info, ifood = await _merchant_ctx(db, tenant_id, merchant_id)
    api = CatalogAPI(ifood)
    try:
        result = await api.update_option(
            info["ifood_merchant_id"],
            option_id,
            name=payload.name,
            price=float(payload.price) if payload.price is not None else None,
            status=payload.status,
            image_path=payload.image_path,
        )
    except IFoodAPIError as e:
        raise HTTPException(
            status_code=400 if 400 <= e.status_code < 500 else 502,
            detail=f"iFood: {e.body}",
        ) from e
    return result or {"status": "updated"}
