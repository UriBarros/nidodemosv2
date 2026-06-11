"""Endpoints de clientes (modelo agência) — onboarding via userCode flow.

Endpoints:
- POST   /clients                  → cria cliente + inicia userCode session
- GET    /clients                  → lista clientes do tenant
- GET    /clients/{id}             → detalhe
- DELETE /clients/{id}             → remove cliente (cascade em merchants)
- POST   /clients/{id}/connect     → reinicia userCode pra cliente existente
- GET    /clients/{id}/poll        → faz polling do iFood; salva tokens se autorizado
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gtrifood.api.deps import get_current_tenant, get_db
from gtrifood.api.schemas import (
    ClientIn,
    ClientOut,
    UserCodePollOut,
    UserCodeSessionOut,
)
from gtrifood.core.security import encrypt
from gtrifood.integrations.ifood.user_code import (
    AuthorizationExpired,
    AuthorizationPending,
    IFoodUserCodeClient,
    IFoodUserCodeError,
    InvalidGrant,
)
from gtrifood.models.db import Client, UserCodeSession
from gtrifood.services.merchants_sync import sync_merchant_for_client

router = APIRouter(prefix="/clients", tags=["clients"])


# =============================================================================
# CRUD básico
# =============================================================================
@router.get("", response_model=list[ClientOut])
async def list_clients(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> list[Client]:
    result = await db.execute(
        select(Client).where(Client.tenant_id == tenant_id).order_by(Client.name)
    )
    return list(result.scalars().all())


@router.get("/{client_id}", response_model=ClientOut)
async def get_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> Client:
    client = await _get_client_or_404(db, tenant_id, client_id)
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> None:
    client = await _get_client_or_404(db, tenant_id, client_id)
    await db.delete(client)
    await db.commit()


# =============================================================================
# Criar cliente + iniciar userCode
# =============================================================================
@router.post("", response_model=UserCodeSessionOut, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> UserCodeSession:
    """Cria cliente novo e já dispara userCode flow. Retorna a sessão com o código."""
    client = Client(
        tenant_id=tenant_id,
        name=payload.name,
        ifood_merchant_id=payload.ifood_merchant_id,
        legal_name=payload.legal_name,
        cnpj=payload.cnpj,
        phone=payload.phone,
        email=payload.email,
        notes=payload.notes,
        status="pending",
    )
    db.add(client)
    await db.flush()  # garante client.id antes da session
    session_obj = await _start_user_code_session(db, tenant_id, client.id)
    await db.commit()
    return session_obj


# =============================================================================
# Reconectar cliente existente (gera novo userCode)
# =============================================================================
@router.post("/{client_id}/connect", response_model=UserCodeSessionOut)
async def reconnect_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> UserCodeSession:
    """Inicia novo userCode pra cliente já cadastrado (ex: token revogado)."""
    client = await _get_client_or_404(db, tenant_id, client_id)
    client.status = "pending"
    session_obj = await _start_user_code_session(db, tenant_id, client.id)
    await db.commit()
    return session_obj


# =============================================================================
# Polling — chama iFood e salva tokens se autorizado
# =============================================================================
@router.get("/{client_id}/poll", response_model=UserCodePollOut)
async def poll_client_authorization(
    client_id: uuid.UUID,
    authorization_code: str | None = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> UserCodePollOut:
    """Frontend chama isto a cada ~5s até status=authorized ou expired.

    Se authorization_code passado: usa ele em vez do user_code da sessão.
    Útil quando iFood gera novo authorizationCode no modal 'Aplicativo
    autorizado' do Portal Parceiro (diferente do userCode original).
    """
    client = await _get_client_or_404(db, tenant_id, client_id)

    # Pega a session pendente mais recente do client
    result = await db.execute(
        select(UserCodeSession)
        .where(
            UserCodeSession.client_id == client_id,
            UserCodeSession.tenant_id == tenant_id,
            UserCodeSession.status == "pending",
        )
        .order_by(UserCodeSession.created_at.desc())
    )
    session_obj = result.scalars().first()
    if not session_obj:
        raise HTTPException(404, "Nenhuma sessão userCode pendente pra este cliente.")

    # Já expirou pelo TTL local?
    now = datetime.now(timezone.utc)
    if session_obj.expires_at < now:
        session_obj.status = "expired"
        client.status = "error"
        client.last_error = "userCode expirou antes do lojista autorizar."
        await db.commit()
        return UserCodePollOut(
            session_id=session_obj.id,
            status="expired",
            message=client.last_error,
            client_status=client.status,
        )

    # Polling no iFood — usa authorization_code passado se houver
    # (iFood gera novo código no Portal após autorização que é diferente
    # do user_code original).
    code_to_use = authorization_code or session_obj.user_code
    ifood = IFoodUserCodeClient()
    try:
        tokens = await ifood.poll(
            authorization_code=code_to_use,
            authorization_code_verifier=session_obj.authorization_code_verifier or "",
        )
    except AuthorizationPending:
        session_obj.last_polled_at = now
        session_obj.poll_count += 1
        await db.commit()
        return UserCodePollOut(
            session_id=session_obj.id,
            status="pending",
            message="Aguardando lojista autorizar no Portal iFood.",
            client_status=client.status,
        )
    except AuthorizationExpired:
        session_obj.status = "expired"
        client.status = "error"
        client.last_error = "userCode expirou."
        await db.commit()
        return UserCodePollOut(
            session_id=session_obj.id,
            status="expired",
            message=client.last_error,
            client_status=client.status,
        )
    except (InvalidGrant, IFoodUserCodeError) as exc:
        session_obj.status = "error"
        session_obj.last_error = str(exc)
        client.status = "error"
        client.last_error = str(exc)
        await db.commit()
        return UserCodePollOut(
            session_id=session_obj.id,
            status="error",
            message=str(exc),
            client_status=client.status,
        )

    # Sucesso — cifra tokens e marca client como conectado
    client.refresh_token_encrypted = encrypt(tokens.refresh_token)
    client.access_token_encrypted = encrypt(tokens.access_token)
    client.token_expires_at = datetime.fromtimestamp(tokens.expires_at, tz=timezone.utc)
    client.token_scope = tokens.scope
    client.status = "connected"
    client.connected_at = now
    client.last_error = None

    session_obj.status = "authorized"
    session_obj.completed_at = now

    await db.commit()

    # Auto-sync do merchant após autorização (best-effort, não bloqueia resposta)
    sync_msg = "Cliente conectado com sucesso."
    try:
        synced = await sync_merchant_for_client(
            tenant_id=tenant_id,
            client_id=client.id,
            ifood_merchant_id=client.ifood_merchant_id,
        )
        if synced > 0:
            sync_msg = f"Cliente conectado. {synced} merchant(s) sincronizado(s)."
    except Exception as exc:  # noqa: BLE001
        # Não derruba o flow — autorização ok, sync pode tentar de novo depois
        sync_msg = f"Cliente conectado, mas falha no sync: {exc}"

    return UserCodePollOut(
        session_id=session_obj.id,
        status="authorized",
        message=sync_msg,
        client_status=client.status,
    )


# =============================================================================
# Helpers
# =============================================================================
async def _get_client_or_404(
    db: AsyncSession, tenant_id: uuid.UUID, client_id: uuid.UUID
) -> Client:
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(404, "cliente não encontrado")
    return client


async def _start_user_code_session(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
) -> UserCodeSession:
    """Chama iFood, cria registro de sessão e retorna."""
    ifood = IFoodUserCodeClient()
    try:
        start = await ifood.start()
    except IFoodUserCodeError as exc:
        # 400 (em vez de 502) — erro de configuração/permissão do iFood,
        # não problema de rede. Mensagem do iFood vai pro frontend.
        raise HTTPException(400, f"iFood não autorizou: {exc}") from exc

    now = datetime.now(timezone.utc)
    session_obj = UserCodeSession(
        tenant_id=tenant_id,
        client_id=client_id,
        user_code=start.user_code,
        verification_url=start.verification_url,
        verification_url_complete=start.verification_url_complete,
        authorization_code_verifier=start.authorization_code_verifier,
        expires_at=now + timedelta(seconds=start.expires_in),
        status="pending",
    )
    db.add(session_obj)
    await db.flush()
    return session_obj
