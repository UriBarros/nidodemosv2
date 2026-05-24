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
    score: int | None
    comment: str | None
    customer_name: str | None
    answered: bool
    answer_text: str | None
    created_at_ifood: datetime | None


class HealthOut(BaseModel):
    status: str
    version: str


class CountOut(BaseModel):
    count: int


class SyncResultOut(BaseModel):
    inserted: int
    message: str
