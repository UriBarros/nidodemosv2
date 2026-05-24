"""Sincroniza merchants do iFood pro banco. Roda manualmente quando precisar.

Uso:
    python scripts/sync_merchants.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gtrifood.core.asyncio_compat import setup_event_loop  # noqa: E402

setup_event_loop()

from gtrifood.core.logging import configure_logging  # noqa: E402
from gtrifood.services.merchants_sync import sync_merchants_for_tenant  # noqa: E402

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")  # tenant interno do seed


async def main() -> int:
    configure_logging()
    print("Sincronizando merchants do iFood...")
    try:
        count = await sync_merchants_for_tenant(TENANT_ID)
        print(f"✅ {count} merchant(s) sincronizado(s).")
        return 0
    except Exception as e:
        print(f"❌ Erro: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
