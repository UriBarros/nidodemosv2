# gtrifood

SaaS multi-cliente para coleta, processamento e visualização de dados do iFood Developer API.

Os lojistas que vendem pelo iFood passam acesso ao app (modelo **Centralizado**), e a plataforma sincroniza pedidos, dados financeiros e avaliações, oferecendo dashboards e relatórios.

## Stack

- **Backend:** Python 3.11+ · FastAPI · httpx async
- **Banco/Auth:** Supabase (Postgres + Auth + RLS)
- **Dashboard:** Streamlit (MVP) — migra para Next.js depois
- **Integração:** iFood Developer API (modelo Centralizada)

## Status

🚧 **Em desenvolvimento — fase inicial.** App iFood de **teste** já configurado (categoria TEST, 1 merchant fictício pré-vinculado, todos os módulos liberados).

## Estrutura

```
gtrifood/
├── src/gtrifood/
│   ├── api/              # FastAPI app + routes
│   ├── core/             # config, db, security
│   ├── integrations/
│   │   └── ifood/        # client OAuth + módulos da API
│   ├── services/         # lógica de sync (orders, financial, reviews)
│   ├── models/           # pydantic + SQLAlchemy
│   └── workers/          # polling de eventos
├── web/                  # Next.js 14 frontend (App Router + shadcn)
├── scripts/              # scripts utilitários (testar auth, etc)
├── supabase/migrations/  # SQL migrations
├── tests/
└── docs/                 # arquitetura, refs iFood
```

## Setup

### 1. Pré-requisitos

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) ou pip
- Conta no [Supabase](https://supabase.com) (projeto criado)
- App **Centralizado** em [developer.ifood.com.br](https://developer.ifood.com.br) com `client_id` + `client_secret`

### 2. Instalar dependências

```bash
# com uv (recomendado)
uv venv
uv pip install -e ".[dev]"

# ou com pip
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
```

### 3. Configurar variáveis de ambiente

```bash
copy .env.example .env          # Windows
# cp .env.example .env          # Linux/Mac
```

Edita `.env` e preenche:
- `IFOOD_CLIENT_ID` + `IFOOD_CLIENT_SECRET` — do app Centralizado de teste
- `SUPABASE_URL` + `SUPABASE_ANON_KEY` + `SUPABASE_SERVICE_ROLE_KEY` — do painel Supabase
- `DATABASE_URL` — connection string Postgres do Supabase
- `ENCRYPTION_KEY` — gera com `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

### 4. Testar autenticação iFood

```bash
python scripts/test_auth.py
```

Espera-se: `access_token` impresso + lista do merchant de teste.

### 5. Rodar tudo (futuro)

```bash
# API
uvicorn gtrifood.api.main:app --reload

# Frontend (Next.js)
cd web && npm run dev
```

## Documentação interna

- [docs/ifood-api.md](docs/ifood-api.md) — referência dos módulos iFood usados
- [docs/architecture.md](docs/architecture.md) — decisões de arquitetura
- [docs/ifood-access.md](docs/ifood-access.md) — fluxo de homologação para produção

## Licença

Privado — uso interno.
