"""Script rápido para validar credenciais iFood.

Uso:
    python scripts/test_auth.py

O que faz:
1. Lê IFOOD_CLIENT_ID / IFOOD_CLIENT_SECRET do .env
2. Chama OAuth client_credentials e exibe access_token (truncado)
3. Lista merchants autorizados (esperado: 1 merchant de teste)

Se tudo der certo, o setup está pronto para começar a implementar features.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Permite rodar o script sem instalar o pacote
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gtrifood.core.asyncio_compat import setup_event_loop  # noqa: E402

setup_event_loop()

from gtrifood.integrations.ifood.auth import IFoodAuthClient, IFoodAuthError  # noqa: E402
from gtrifood.integrations.ifood.client import IFoodAPIError, IFoodClient  # noqa: E402
from gtrifood.integrations.ifood.merchants import MerchantAPI  # noqa: E402


async def main() -> int:
    print("=" * 60)
    print("Teste de autenticação iFood Developer API")
    print("=" * 60)

    # 1. Autenticação
    print("\n[1/2] Solicitando access_token...")
    auth = IFoodAuthClient()
    try:
        token = await auth.get_token()
    except IFoodAuthError as e:
        print(f"❌ Erro na autenticação: {e}")
        print("\nChecklist:")
        print("  - IFOOD_CLIENT_ID e IFOOD_CLIENT_SECRET corretos no .env?")
        print("  - App ainda existe em developer.ifood.com.br?")
        return 1
    print(f"✅ access_token obtido (prefixo: {token[:20]}...)")

    # 2. Listar merchants
    print("\n[2/2] Listando merchants autorizados...")
    client = IFoodClient()
    api = MerchantAPI(client)
    try:
        merchants = await api.list_merchants()
    except IFoodAPIError as e:
        print(f"❌ Erro ao listar merchants: {e}")
        return 1

    if not merchants:
        print("⚠️  Nenhum merchant retornado. Verifique a aba 'Permissões' do app.")
        return 1

    print(f"✅ {len(merchants)} merchant(s) encontrado(s):\n")
    for m in merchants:
        mid = m.get("id", "?")
        name = m.get("name") or m.get("corporateName", "?")
        print(f"  - {name}")
        print(f"    id: {mid}")

    print("\n🎉 Setup OK! Próximo passo: rodar o backend FastAPI.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
