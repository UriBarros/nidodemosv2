"""Endpoints do módulo Catalog (cardápio) — API v2.0 atualizada.

Workflow alinhado com docs oficiais:
- Listas locais (já sincronizadas no DB) via GET
- Criação: POST /categories e POST /items (compõe payload aninhado)
- Edição rápida: PATCH /items/{id}/status, /items/{id}/price (endpoints
  dedicados do iFood)
- Edição estrutural (nome/descrição/foto/complementos): PATCH /items/{id}
  internamente reconstrói o payload completo e envia PUT pro iFood
- Sync: POST /catalog/sync re-puxa tudo
"""

from __future__ import annotations

import uuid
from copy import deepcopy

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
from gtrifood.integrations.ifood.catalog import CatalogAPI, new_uuid
from gtrifood.integrations.ifood.client import IFoodAPIError, IFoodClient
from gtrifood.models.db import CatalogCategory, CatalogItem, Merchant
from gtrifood.services.catalog_sync import sync_catalog_for_merchant

router = APIRouter(prefix="/catalog", tags=["catalog"])


# =============================================================================
# Listar categorias (DB local)
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
# Helpers de contexto
# =============================================================================
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


async def _get_merchant_for_item(db: AsyncSession, item: CatalogItem) -> dict:
    result = await db.execute(
        select(Merchant.ifood_merchant_id, Merchant.client_id).where(
            Merchant.id == item.merchant_id
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "merchant do item não encontrado")
    return {"ifood_merchant_id": row[0], "client_id": row[1]}


# =============================================================================
# Atualizar status do item (endpoint dedicado iFood)
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
            status_code=400 if 400 <= e.status_code < 500 else 502,
            detail=f"iFood rejeitou status: {e.body}",
        ) from e

    item.status = new_status
    await db.commit()
    await db.refresh(item)
    return item


# =============================================================================
# Atualizar preço do item (endpoint dedicado iFood)
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
            status_code=400 if 400 <= e.status_code < 500 else 502,
            detail=f"iFood rejeitou preço: {e.body}",
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
    counts = await sync_catalog_for_merchant(merchant_id)
    return CatalogSyncOut(
        merchant_id=merchant_id,
        categories=counts["categories"],
        items=counts["items"],
    )


# =============================================================================
# Criar categoria (POST /categories direto, sem catalogId)
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

    try:
        result = await api.create_category(
            info["ifood_merchant_id"],
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
# Criar item (PUT idempotente iFood, com estrutura aninhada)
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

    item_id = new_uuid()
    body = CatalogAPI.build_simple_item(
        category_id=ifood_cat,
        name=payload.name.strip(),
        price=float(payload.price),
        description=payload.description,
        status=payload.status,
        external_code=payload.external_code,
        image_path=payload.image_path,
        item_id=item_id,
    )

    try:
        await api.put_item(info["ifood_merchant_id"], body)
    except IFoodAPIError as e:
        raise HTTPException(
            status_code=400 if 400 <= e.status_code < 500 else 502,
            detail=f"iFood: {e.body}",
        ) from e
    return {"status": "created", "ifood_item_id": item_id, "payload": body}


# =============================================================================
# Atualizar item (nome/descrição/foto) — reenvia PUT completo
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

    # Reconstrói payload a partir de raw_data (último estado conhecido)
    # ou monta payload mínimo se raw_data estiver vazio.
    raw = deepcopy(item.raw_data or {})
    payload_body: dict = raw if "item" in raw else {
        "item": {
            "id": item.ifood_item_id,
            "type": "DEFAULT",
            "categoryId": _ifood_category_id_for_item(item) or "",
            "status": item.status,
            "price": {"value": float(item.price or 0)},
        },
        "products": [],
        "optionGroups": [],
        "options": [],
    }

    # Aplica updates
    item_dict = payload_body.setdefault("item", {})
    products = payload_body.setdefault("products", [])

    if payload.name is not None:
        # nome do item está em products[0].name (estrutura iFood)
        if products:
            products[0]["name"] = payload.name
        else:
            products.append({"id": new_uuid(), "name": payload.name})
    if payload.description is not None and products:
        products[0]["description"] = payload.description
    if payload.image_path is not None:
        item_dict["imagePath"] = payload.image_path
    if payload.external_code is not None:
        item_dict["externalCode"] = payload.external_code

    payload_body["item"] = item_dict
    payload_body["products"] = products
    payload_body.setdefault("optionGroups", [])
    payload_body.setdefault("options", [])

    try:
        await api.put_item(merchant_info["ifood_merchant_id"], payload_body)
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
    item.raw_data = payload_body
    await db.commit()
    await db.refresh(item)
    return item


def _ifood_category_id_for_item(item: CatalogItem) -> str | None:
    """Tenta extrair ifood_category_id do raw_data do item."""
    raw = item.raw_data or {}
    return raw.get("item", {}).get("categoryId") or raw.get("categoryId")


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
# Complementos — agora gerenciados via PUT do item completo
# =============================================================================
# Os endpoints abaixo NÃO criam grupos/opções independentemente:
# eles modificam o item existente reenviando o PUT completo.
@router.get("/option-groups")
async def list_option_groups(
    merchant_id: uuid.UUID,
    item_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> list[dict]:
    """Lista grupos de complementos de um item (extraído de raw_data) ou
    busca todos do merchant via list_items_in_category iFood.
    """
    if item_id:
        item = await _get_item_or_404(db, tenant_id, item_id)
        raw = item.raw_data or {}
        groups = raw.get("optionGroups", [])
        # Enriquece com opções correspondentes
        options_by_id: dict[str, list[dict]] = {}
        for opt in raw.get("options", []):
            gid = opt.get("optionGroupId")
            if not gid:
                continue
            options_by_id.setdefault(gid, []).append(opt)
        for g in groups:
            g["options"] = options_by_id.get(g.get("id"), [])
        return groups
    return []


@router.post("/option-groups", status_code=201)
async def create_option_group(
    payload: OptionGroupCreateIn,
    item_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict:
    """Cria grupo de complementos vinculado a um item (PUT do item completo)."""
    if not payload.name.strip():
        raise HTTPException(400, "nome obrigatório")
    item = await _get_item_or_404(db, tenant_id, item_id)
    merchant_info = await _get_merchant_for_item(db, item)
    ifood = await _ifood_for_merchant(merchant_info)
    api = CatalogAPI(ifood)

    raw = deepcopy(item.raw_data or {})
    if "item" not in raw:
        raise HTTPException(409, "item sem raw_data — re-sincronize antes")

    new_group_id = new_uuid()
    new_group = {
        "id": new_group_id,
        "name": payload.name.strip(),
        "status": "AVAILABLE",
        "min": int(payload.min_choices),
        "max": int(payload.max_choices),
        "optionGroupType": "OFFER_UNIT",
        "optionIds": [],
    }
    raw.setdefault("optionGroups", []).append(new_group)
    raw.setdefault("options", [])
    raw.setdefault("products", [])

    try:
        await api.put_item(merchant_info["ifood_merchant_id"], raw)
    except IFoodAPIError as e:
        raise HTTPException(
            status_code=400 if 400 <= e.status_code < 500 else 502,
            detail=f"iFood: {e.body}",
        ) from e

    item.raw_data = raw
    await db.commit()
    return {"status": "created", "option_group_id": new_group_id}


@router.post("/options", status_code=201)
async def create_option(
    payload: OptionCreateIn,
    item_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict:
    """Cria opção dentro de um grupo (PUT do item completo)."""
    if not payload.name.strip():
        raise HTTPException(400, "nome obrigatório")
    if payload.price < 0:
        raise HTTPException(400, "preço não pode ser negativo")

    item = await _get_item_or_404(db, tenant_id, item_id)
    merchant_info = await _get_merchant_for_item(db, item)
    ifood = await _ifood_for_merchant(merchant_info)
    api = CatalogAPI(ifood)

    raw = deepcopy(item.raw_data or {})
    if "item" not in raw:
        raise HTTPException(409, "item sem raw_data — re-sincronize antes")

    # Cria produto e opção
    product_id = new_uuid()
    option_id = new_uuid()
    raw.setdefault("products", []).append(
        {"id": product_id, "name": payload.name.strip()}
    )
    raw.setdefault("options", []).append(
        {
            "id": option_id,
            "optionGroupId": payload.option_group_id,
            "productId": product_id,
            "status": payload.status,
            "price": {"value": float(payload.price)},
        }
    )
    # Atualiza optionIds do grupo correspondente
    for g in raw.get("optionGroups", []):
        if g.get("id") == payload.option_group_id:
            g.setdefault("optionIds", []).append(option_id)
            break
    raw.setdefault("optionGroups", [])

    try:
        await api.put_item(merchant_info["ifood_merchant_id"], raw)
    except IFoodAPIError as e:
        raise HTTPException(
            status_code=400 if 400 <= e.status_code < 500 else 502,
            detail=f"iFood: {e.body}",
        ) from e

    item.raw_data = raw
    await db.commit()
    return {"status": "created", "option_id": option_id}


@router.patch("/options/{option_id}")
async def update_option(
    option_id: str,
    payload: OptionUpdateIn,
    merchant_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> dict:
    """Atualiza status/preço de uma opção via endpoints PATCH dedicados."""
    _, info, ifood = await _merchant_ctx(db, tenant_id, merchant_id)
    api = CatalogAPI(ifood)

    try:
        if payload.status is not None:
            await api.update_option_status(
                info["ifood_merchant_id"], option_id, payload.status.upper()
            )
        if payload.price is not None:
            await api.update_option_price(
                info["ifood_merchant_id"], option_id, float(payload.price)
            )
    except IFoodAPIError as e:
        raise HTTPException(
            status_code=400 if 400 <= e.status_code < 500 else 502,
            detail=f"iFood: {e.body}",
        ) from e
    return {"status": "updated"}
