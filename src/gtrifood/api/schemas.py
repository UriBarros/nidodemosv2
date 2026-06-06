"""Pydantic schemas de resposta da API (DTOs)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class MerchantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ifood_merchant_id: str
    name: str
    corporate_name: str | None
    cnpj: str | None
    status: str
    created_at: datetime


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    merchant_id: uuid.UUID
    ifood_order_id: str
    display_id: str | None
    status: str
    order_type: str | None
    created_at_ifood: datetime | None
    total_amount: Decimal | None
    customer_name: str | None
    synced_at: datetime


class OrderDetailOut(BaseModel):
    """Pedido completo com raw_data (todos os campos do iFood)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    merchant_id: uuid.UUID
    ifood_order_id: str
    display_id: str | None
    status: str
    order_type: str | None
    created_at_ifood: datetime | None
    total_amount: Decimal | None
    customer_name: str | None
    raw_data: dict
    synced_at: datetime
    updated_at: datetime
    updated_at: datetime


class OrderEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ifood_event_id: str
    ifood_order_id: str | None
    code: str
    full_code: str | None
    acknowledged_at: datetime | None
    received_at: datetime


class FinancialEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    merchant_id: uuid.UUID
    event_type: str
    competence_date: date | None
    amount: Decimal
    description: str | None
    synced_at: datetime


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    merchant_id: uuid.UUID
    ifood_review_id: str
    ifood_order_id: str | None
    score: int | None
    comment: str | None
    customer_name: str | None
    answered: bool
    answer_text: str | None
    created_at_ifood: datetime | None


class ReviewReplyIn(BaseModel):
    """Payload pra responder uma avaliação."""

    text: str


# =============================================================================
# Merchant — interrupções + horários
# =============================================================================
class InterruptionIn(BaseModel):
    description: str
    start: datetime
    end: datetime


class ShiftIn(BaseModel):
    """Um turno de funcionamento em 1 dia.

    Ex: sábado das 10 às 19 = dayOfWeek=SATURDAY, start='10:00:00', duration=540
    (540 min = 9h). Múltiplos shifts no mesmo dia para intervalos.
    """

    dayOfWeek: str  # MONDAY, TUESDAY, ..., SUNDAY
    start: str      # HH:MM:SS
    duration: int   # minutos


class OpeningHoursIn(BaseModel):
    shifts: list[ShiftIn]


class HealthOut(BaseModel):
    status: str
    version: str


class CountOut(BaseModel):
    count: int


class SyncResultOut(BaseModel):
    inserted: int
    message: str


# =============================================================================
# Clients (modelo agência)
# =============================================================================
class ClientIn(BaseModel):
    """Payload pra criar/atualizar um cliente lojista."""

    name: str
    ifood_merchant_id: str | None = None  # UUID iFood — operador cola do Portal Gestor
    legal_name: str | None = None
    cnpj: str | None = None
    phone: str | None = None
    email: str | None = None
    notes: str | None = None


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    ifood_merchant_id: str | None
    legal_name: str | None
    cnpj: str | None
    phone: str | None
    email: str | None
    notes: str | None
    status: str
    connected_at: datetime | None
    disconnected_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class UserCodeSessionOut(BaseModel):
    """Resposta ao iniciar sessão userCode pra um cliente."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID | None
    user_code: str
    verification_url: str
    verification_url_complete: str | None
    expires_at: datetime
    status: str
    poll_count: int


class UserCodePollOut(BaseModel):
    """Resposta do polling — status atual + tokens (se autorizado)."""

    session_id: uuid.UUID
    status: str                              # pending | authorized | expired | error
    message: str | None = None
    client_status: str | None = None         # status do client após poll


# =============================================================================
# Catalog
# =============================================================================
class CatalogCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    merchant_id: uuid.UUID
    ifood_category_id: str
    name: str
    external_code: str | None
    status: str
    sequence: int
    synced_at: datetime


class CatalogItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    merchant_id: uuid.UUID
    category_id: uuid.UUID | None
    ifood_item_id: str
    name: str
    description: str | None
    external_code: str | None
    price: Decimal | None
    original_price: Decimal | None
    status: str
    image_path: str | None
    synced_at: datetime


class CatalogItemStatusIn(BaseModel):
    status: str  # AVAILABLE | UNAVAILABLE


class CatalogItemPriceIn(BaseModel):
    price: Decimal


class CatalogSyncOut(BaseModel):
    merchant_id: uuid.UUID
    categories: int
    items: int


# ===== Cria/Edita catalog =====
class CategoryCreateIn(BaseModel):
    merchant_id: uuid.UUID
    name: str
    external_code: str | None = None


class ItemCreateIn(BaseModel):
    merchant_id: uuid.UUID
    category_id: uuid.UUID
    name: str
    description: str | None = None
    price: Decimal
    status: str = "AVAILABLE"
    external_code: str | None = None
    image_path: str | None = None


class ItemUpdateIn(BaseModel):
    name: str | None = None
    description: str | None = None
    image_path: str | None = None
    external_code: str | None = None


# ===== Option groups =====
class OptionGroupCreateIn(BaseModel):
    merchant_id: uuid.UUID
    name: str
    min_choices: int = 0
    max_choices: int = 1
    external_code: str | None = None


class OptionCreateIn(BaseModel):
    merchant_id: uuid.UUID
    option_group_id: str  # ifood id
    name: str
    price: Decimal
    status: str = "AVAILABLE"
    image_path: str | None = None
    external_code: str | None = None


class OptionUpdateIn(BaseModel):
    name: str | None = None
    price: Decimal | None = None
    status: str | None = None
    image_path: str | None = None
