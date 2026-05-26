"""Service: gestão de access_token por client lojista (modelo Distribuída).

Cada client tem refresh_token cifrado. Esta camada decifra, valida expiração,
faz refresh on-demand chamando iFood, e atualiza o DB com tokens novos.

Uso típico no worker:
    token = await get_or_refresh_access_token(client_id)
    ifood = IFoodClient(token_provider=lambda: token)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gtrifood.core.db import get_session
from gtrifood.core.logging import get_logger
from gtrifood.core.security import decrypt, encrypt
from gtrifood.integrations.ifood.user_code import (
    IFoodUserCodeClient,
    IFoodUserCodeError,
    InvalidGrant,
)
from gtrifood.models.db import Client

_log = get_logger("client_tokens")


class ClientNotConnected(Exception):
    """Client não tem tokens válidos pra acessar iFood."""


async def get_or_refresh_access_token(client_id: uuid.UUID) -> str:
    """Retorna access_token decifrado e válido pra um client.

    - Se ainda não expirou: retorna o access_token cacheado.
    - Se expirou: chama iFood refresh, persiste tokens novos, retorna.
    - Se refresh falhar (token revogado): marca client como 'disconnected'.
    """
    async with get_session() as session:
        client = await _load_client(session, client_id)

        # Token válido cacheado?
        if _token_is_fresh(client):
            return decrypt(client.access_token_encrypted or "")

        # Precisa refresh
        if not client.refresh_token_encrypted:
            raise ClientNotConnected(
                f"Client {client_id} sem refresh_token — reconectar via userCode."
            )

        refresh_token = decrypt(client.refresh_token_encrypted)
        ifood = IFoodUserCodeClient()
        try:
            new_tokens = await ifood.refresh(refresh_token)
        except InvalidGrant as exc:
            client.status = "disconnected"
            client.disconnected_at = datetime.now(timezone.utc)
            client.last_error = f"refresh_token revogado: {exc}"
            await session.commit()
            raise ClientNotConnected(client.last_error) from exc
        except IFoodUserCodeError as exc:
            client.last_error = f"refresh falhou: {exc}"
            await session.commit()
            raise ClientNotConnected(client.last_error) from exc

        # Persiste tokens novos (refresh_token pode ter rotacionado)
        client.access_token_encrypted = encrypt(new_tokens.access_token)
        client.refresh_token_encrypted = encrypt(new_tokens.refresh_token)
        client.token_expires_at = datetime.fromtimestamp(
            new_tokens.expires_at, tz=timezone.utc
        )
        client.token_scope = new_tokens.scope
        client.last_error = None
        await session.commit()

        _log.info("token_refreshed", client_id=str(client_id))
        return new_tokens.access_token


async def list_connected_client_ids() -> list[uuid.UUID]:
    """Retorna IDs de todos clients em status 'connected' pro worker iterar."""
    async with get_session() as session:
        result = await session.execute(
            select(Client.id).where(Client.status == "connected")
        )
        return [row[0] for row in result.all()]


# =============================================================================
# Helpers internos
# =============================================================================
async def _load_client(session: AsyncSession, client_id: uuid.UUID) -> Client:
    result = await session.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise ClientNotConnected(f"Client {client_id} não encontrado")
    return client


def _token_is_fresh(client: Client) -> bool:
    """access_token ainda válido (com margem de 5min)?"""
    if not client.access_token_encrypted or not client.token_expires_at:
        return False
    now = datetime.now(timezone.utc)
    # token_expires_at já considera margem de 5min (set em parse_token)
    return client.token_expires_at > now
