# Arquitetura — gtrifood

## Visão geral

```
┌──────────────────────────────────────────────────────────────┐
│                  iFood Developer API                          │
│   /merchants  /orders  /events  /financial  /reviews          │
└────────────────────────┬─────────────────────────────────────┘
                         │  HTTPS + Bearer token
                         ▼
┌──────────────────────────────────────────────────────────────┐
│   gtrifood backend (Python · FastAPI)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │ Events       │  │ Sync         │  │ FastAPI routes   │    │
│  │ poller       │→ │ services     │← │ /merchants /...  │    │
│  │ (worker)     │  │              │  │                  │    │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘    │
│         │                 │                   │              │
└─────────┼─────────────────┼───────────────────┼──────────────┘
          │                 │                   │
          ▼                 ▼                   ▼
┌──────────────────────────────────────────────────────────────┐
│              Supabase (Postgres + Auth + RLS)                 │
│   tenants  users  ifood_credentials  merchants                │
│   orders   financial_events  reviews                          │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│   Next.js 14 frontend (App Router + shadcn/ui)                │
└──────────────────────────────────────────────────────────────┘
```

## Componentes

### 1. iFood integration layer (`src/gtrifood/integrations/ifood/`)
- Stateless. Não toca no banco.
- `auth.py` — gerencia token (cache em memória)
- `client.py` — HTTP base com retry e tratamento de erro
- Um módulo por área da API: `merchants.py`, `orders.py`, `events.py`, etc.

### 2. Services (`src/gtrifood/services/`)
- Orquestram: chama iFood → transforma → persiste no Postgres.
- `orders_sync.py` — fetch + persist pedidos
- `financial_sync.py` — sync periódico financeiro
- `reviews_sync.py` — sync reviews

### 3. Workers (`src/gtrifood/workers/`)
- Processos longos.
- `events_poller.py` — loop infinito de polling de eventos (30s).

### 4. API (`src/gtrifood/api/`)
- FastAPI. Expõe dados para o frontend.
- Auth via Supabase JWT.
- Routes por domínio: merchants, orders, financial, reviews.

### 5. Frontend (`web/`)
- Next.js 14 (App Router) + shadcn/ui + Tailwind + TanStack Query.
- Login Supabase → seleciona merchant → vê páginas (Pedidos, Financeiro, Reviews).
- Bundle standalone Docker, servido em `gtrifood.aceleradoragtr.cloud/`.

### 6. Database (Supabase Postgres)
- Multi-tenant via `tenant_id` em toda tabela.
- RLS habilitado — cada usuário vê só dados do tenant dele.

## Multi-tenancy

Cada **cliente** do gtrifood = 1 `tenant`.
Cada tenant pode ter **vários merchants iFood** (no modelo Centralizada em produção).

Hoje (teste): 1 tenant interno + 1 merchant fictício do iFood.

## Segurança

- Credenciais iFood **nunca** em código. Só em `.env` (dev) ou em variáveis de ambiente do deploy.
- Tokens de refresh (quando houver, em produção) cifrados com `Fernet` antes de ir pro banco.
- RLS no Postgres impede vazamento entre tenants.
- HTTPS obrigatório em produção.
- Logs nunca incluem `client_secret`, `access_token`, ou dados pessoais (LGPD).

## Por que essas escolhas

- **Python FastAPI**: ecossistema forte pra ETL e dados; async nativo; tipagem com pydantic.
- **Supabase**: Postgres + Auth + RLS prontos. Acelera MVP. Sem custo inicial alto.
- **Next.js 14 + shadcn/ui**: frontend produção com SSR/SSG, App Router e tipagem ponta-a-ponta. Streamlit foi MVP, foi removido depois que UI ficou crítica.
- **httpx async**: chamadas paralelas a múltiplos merchants em produção; melhor que requests sync.
- **Polling de eventos** (não webhook) no início: app de teste não tem URL pública; polling funciona em qualquer ambiente.
