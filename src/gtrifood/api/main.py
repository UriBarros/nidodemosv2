"""Entry point do FastAPI app.

Rodar:
    uvicorn gtrifood.api.main:app --reload --host 0.0.0.0 --port 8000

OpenAPI/Swagger UI:
    http://localhost:8000/docs
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gtrifood import __version__
from gtrifood.api.routes import financial, health, merchants, orders, reviews
from gtrifood.core.asyncio_compat import setup_event_loop
from gtrifood.core.logging import configure_logging

# Windows compat — antes de qualquer asyncio
setup_event_loop()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    yield


# Root path pro Swagger/OpenAPI funcionar atrás de proxy (Traefik StripPrefix).
# Ex: API_ROOT_PATH=/api → docs em https://host/api/docs com URLs corretas.
_root_path = os.getenv("API_ROOT_PATH", "")

app = FastAPI(
    title="gtrifood API",
    version=__version__,
    description="API REST do gtrifood — dados iFood Developer para dashboards.",
    lifespan=lifespan,
    root_path=_root_path,
)

# CORS — abre tudo no MVP local. Em prod, restringir origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(merchants.router)
app.include_router(orders.router)
app.include_router(financial.router)
app.include_router(reviews.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"app": "gtrifood", "version": __version__, "docs": "/docs"}
