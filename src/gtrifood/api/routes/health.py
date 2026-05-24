"""Health check — usado por probes e pelo dashboard."""

from __future__ import annotations

from fastapi import APIRouter

from gtrifood import __version__
from gtrifood.api.schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
async def health() -> HealthOut:
    return HealthOut(status="ok", version=__version__)
