"""Roda o worker de polling de eventos.

Uso:
    python scripts/run_poller.py

Ctrl+C pra parar.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gtrifood.core.asyncio_compat import setup_event_loop  # noqa: E402

setup_event_loop()

from gtrifood.workers.events_poller import main as poller_main  # noqa: E402

if __name__ == "__main__":
    try:
        asyncio.run(poller_main())
    except KeyboardInterrupt:
        print("\nEncerrado.")
