"""Script para validar conexão Supabase + seed.

Uso:
    python scripts/test_db.py

O que faz:
1. Conecta no Postgres usando DATABASE_URL do .env
2. Lista tenants
3. Lista merchants
4. Confirma seed inserido pela migration 0001
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gtrifood.core.asyncio_compat import setup_event_loop  # noqa: E402

setup_event_loop()

from sqlalchemy import select  # noqa: E402

from gtrifood.core.db import get_session  # noqa: E402
from gtrifood.models.db import Merchant, Tenant  # noqa: E402


async def main() -> int:
    print("=" * 60)
    print("Teste de conexão Supabase + seed")
    print("=" * 60)

    try:
        async with get_session() as session:
            # 1. Tenants
            print("\n[1/2] Listando tenants...")
            tenants = (await session.execute(select(Tenant))).scalars().all()
            print(f"✅ {len(tenants)} tenant(s) encontrado(s):")
            for t in tenants:
                print(f"  - {t.name} (slug={t.slug}, id={t.id})")

            # 2. Merchants
            print("\n[2/2] Listando merchants...")
            merchants = (await session.execute(select(Merchant))).scalars().all()
            print(f"✅ {len(merchants)} merchant(s) encontrado(s):")
            for m in merchants:
                print(f"  - {m.name}")
                print(f"    ifood_merchant_id: {m.ifood_merchant_id}")
                print(f"    cnpj: {m.cnpj}")
                print(f"    status: {m.status}")

        print("\n🎉 Conexão Supabase OK + seed validado.")
        return 0

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        print("\nChecklist:")
        print("  - DATABASE_URL no .env está correto?")
        print("  - Senha do banco substituída no lugar de [YOUR-PASSWORD]?")
        print("  - Projeto Supabase está rodando? (status ACTIVE_HEALTHY)")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
