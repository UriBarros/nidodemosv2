"""Compatibilidade de event loop pra Windows.

psycopg async requer SelectorEventLoop, mas Windows usa ProactorEventLoop por default.
Chama `setup_event_loop()` no início de cada entry point (scripts, workers, app).
"""

from __future__ import annotations

import asyncio
import sys


def setup_event_loop() -> None:
    """Configura SelectorEventLoop no Windows. No-op em outros SOs."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
