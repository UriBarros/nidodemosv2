"""iFood userCode (Device Authorization) flow — onboarding de merchants.

Diferente do client_credentials (auth.py), este flow conecta um lojista específico:

1. start() → backend chama POST /oauth/userCode → recebe userCode + URL.
2. Mostra userCode + URL pro lojista (manda no WhatsApp/email).
3. Lojista abre URL, faz login no Portal iFood, autoriza o app.
4. poll() → backend tenta trocar (authorizationCode + verifier) por token.
   - Enquanto lojista não autorizou: erro `authorization_pending`.
   - Após autorizar: retorna access_token + refresh_token.
5. refresh() → renova access_token usando refresh_token quando expirar.

Tokens cifrados pela camada de persistência (Fernet com ENCRYPTION_KEY).

Referências:
- https://developer.ifood.com.br/pt-BR/docs/references/authentication/
- iFood usa um device-flow proprietário (não exatamente RFC 8628), mas é similar.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from gtrifood.config import Settings, get_settings


# =============================================================================
# Tipos de resposta
# =============================================================================
@dataclass
class UserCodeStart:
    """Dados retornados ao iniciar uma sessão userCode."""

    user_code: str                          # Ex: "ABCD12"
    verification_url: str                   # Ex: https://portal.ifood.com.br/apps/code
    verification_url_complete: str          # URL com query string pra atalho
    authorization_code_verifier: str        # Token interno pra trocar por access_token
    expires_in: int                         # Segundos até expirar (~600 = 10min)


@dataclass
class TokenPair:
    """access_token + refresh_token retornados pelo iFood."""

    access_token: str
    refresh_token: str
    expires_in: int                         # TTL do access_token (segundos)
    token_type: str                         # geralmente "bearer"
    scope: str | None = None

    @property
    def expires_at(self) -> float:
        """Unix timestamp de expiração (com margem de 5min)."""
        return time.time() + max(0, self.expires_in - 300)


# =============================================================================
# Exceções
# =============================================================================
class IFoodUserCodeError(Exception):
    """Base pra erros do userCode flow."""


class AuthorizationPending(IFoodUserCodeError):
    """Lojista ainda não autorizou — continuar polling."""


class AuthorizationExpired(IFoodUserCodeError):
    """userCode expirou. Iniciar nova sessão."""


class InvalidGrant(IFoodUserCodeError):
    """authorizationCode inválido ou já consumido."""


# =============================================================================
# Cliente
# =============================================================================
class IFoodUserCodeClient:
    """Cliente do userCode flow do iFood Developer API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def _base_url(self) -> str:
        return self._settings.ifood_auth_url.rsplit("/oauth/", 1)[0]

    async def start(self) -> UserCodeStart:
        """Inicia uma sessão userCode. Retorna o código que o lojista deve usar.

        Não usa retry em 4xx (erro de cliente — retry não resolve, só esconde causa).
        Retry só em erros transitórios (5xx, timeout, transport).
        """
        url = f"{self._base_url}/oauth/userCode"
        data = {
            "clientId": self._settings.ifood_client_id.get_secret_value(),
        }
        # Retry só transient errors (não 4xx)
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        url,
                        data=data,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                if attempt == 2:
                    raise IFoodUserCodeError(f"timeout/transport iFood: {exc}") from exc
                continue

            # 4xx: erro permanente, não retry
            if 400 <= response.status_code < 500:
                # Tenta extrair detalhes do body do iFood
                try:
                    body = response.json()
                    detail = (
                        body.get("error_description")
                        or body.get("error")
                        or body.get("message")
                        or response.text
                    )
                except Exception:
                    detail = response.text
                raise IFoodUserCodeError(
                    f"iFood rejeitou userCode [{response.status_code}]: {detail}"
                )

            # 5xx: retry
            if response.status_code >= 500:
                if attempt == 2:
                    raise IFoodUserCodeError(
                        f"iFood instável [{response.status_code}]: {response.text}"
                    )
                continue

            # 200: sucesso
            payload = response.json()
            return UserCodeStart(
                user_code=payload["userCode"],
                verification_url=payload["verificationUrl"],
                verification_url_complete=payload.get(
                    "verificationUrlComplete", payload["verificationUrl"]
                ),
                authorization_code_verifier=payload["authorizationCodeVerifier"],
                expires_in=int(payload.get("expiresIn", 600)),
            )

        raise IFoodUserCodeError("start userCode falhou após 3 tentativas")

    async def poll(
        self,
        authorization_code: str,
        authorization_code_verifier: str,
    ) -> TokenPair:
        """Troca authorizationCode + verifier por access_token + refresh_token.

        Levanta AuthorizationPending enquanto o lojista não autorizou.
        Levanta AuthorizationExpired se o userCode passou do TTL.
        Levanta InvalidGrant se o code/verifier estiverem incorretos.
        """
        url = f"{self._base_url}/oauth/token"
        data = {
            "grantType": "authorization_code",
            "clientId": self._settings.ifood_client_id.get_secret_value(),
            "clientSecret": self._settings.ifood_client_secret.get_secret_value(),
            "authorizationCode": authorization_code,
            "authorizationCodeVerifier": authorization_code_verifier,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if response.status_code == 200:
            return self._parse_token(response.json())

        # iFood usa códigos de erro custom no body (não segue RFC OAuth2 device flow).
        # Observações empíricas com app Distribuído de TEST:
        # - Enquanto lojista NÃO autorizou: 401 Unauthorized com
        #   {"error":{"code":"Unauthorized","message":"Invalid authorization code XXX"}}
        # - Após autorizar: 200 com tokens
        # - Após expirar: 410 Gone ou 400 com "expired" no body
        body = response.text.lower()

        if "expired" in body or response.status_code == 410:
            raise AuthorizationExpired("userCode expirou. Iniciar nova sessão.")

        # 401 + "invalid authorization code" do iFood = lojista ainda não autorizou
        # (counter-intuitivo, mas é como a API se comporta).
        if response.status_code == 401 and "invalid authorization code" in body:
            raise AuthorizationPending("Lojista ainda não autorizou no Portal iFood.")

        if "pending" in body or response.status_code == 428:
            raise AuthorizationPending("Lojista ainda não autorizou.")

        if response.status_code in (400, 401):
            raise InvalidGrant(f"authorization_code inválido: {response.text}")

        raise IFoodUserCodeError(
            f"poll falhou [{response.status_code}]: {response.text}"
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def refresh(self, refresh_token: str) -> TokenPair:
        """Renova access_token usando refresh_token.

        iFood pode retornar refresh_token novo (rotação) — sempre persistir
        o refresh_token retornado.
        """
        url = f"{self._base_url}/oauth/token"
        data = {
            "grantType": "refresh_token",
            "clientId": self._settings.ifood_client_id.get_secret_value(),
            "clientSecret": self._settings.ifood_client_secret.get_secret_value(),
            "refreshToken": refresh_token,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if response.status_code != 200:
            if response.status_code in (400, 401):
                raise InvalidGrant(
                    f"refresh_token inválido ou revogado: {response.text}"
                )
            raise IFoodUserCodeError(
                f"refresh falhou [{response.status_code}]: {response.text}"
            )

        return self._parse_token(response.json())

    @staticmethod
    def _parse_token(payload: dict) -> TokenPair:
        return TokenPair(
            access_token=payload["accessToken"],
            refresh_token=payload["refreshToken"],
            expires_in=int(payload.get("expiresIn", 10800)),  # 3h default
            token_type=payload.get("type", "bearer"),
            scope=payload.get("scope"),
        )
