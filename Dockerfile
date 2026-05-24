# =============================================================================
# gtrifood — imagem única servindo API, worker e dashboard.
# O serviço escolhido roda via `command:` do docker-compose.
# =============================================================================
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/app/.venv/bin:$PATH"

# psycopg precisa de libpq + build tools temporários
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependências primeiro (cache de layer)
COPY pyproject.toml ./
RUN python -m venv .venv \
    && .venv/bin/pip install -U pip setuptools wheel \
    && .venv/bin/pip install -e .

# Código depois (invalida cache só quando muda)
COPY src ./src
COPY dashboard ./dashboard
COPY scripts ./scripts
COPY supabase ./supabase

# Reinstala em modo editable agora que src/ existe (para registrar pacote)
RUN .venv/bin/pip install -e .

EXPOSE 8000 8501

# Default = API. Sobrescrito no docker-compose para worker/dashboard.
CMD ["uvicorn", "gtrifood.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
