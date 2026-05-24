-- =============================================================================
-- gtrifood — migration inicial (0001_init)
-- Schema multi-tenant para SaaS de dados iFood.
--
-- Modelo: cada cliente do gtrifood = 1 `tenant`.
-- Cada tenant tem 1+ merchants iFood vinculados.
-- RLS isola dados por tenant.
-- =============================================================================

-- Extensões necessárias
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- =============================================================================
-- 1. TENANTS — cada cliente do SaaS
-- =============================================================================
create table public.tenants (
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    slug text not null unique,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

comment on table public.tenants is 'Clientes da plataforma gtrifood. Cada tenant agrupa users + merchants iFood.';

-- =============================================================================
-- 2. TENANT_USERS — vínculo entre auth.users (Supabase Auth) e tenants
-- =============================================================================
create table public.tenant_users (
    tenant_id uuid not null references public.tenants(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    role text not null default 'member' check (role in ('owner', 'admin', 'member')),
    created_at timestamptz not null default now(),
    primary key (tenant_id, user_id)
);

create index idx_tenant_users_user on public.tenant_users(user_id);

-- =============================================================================
-- 3. IFOOD_CREDENTIALS — credenciais de app iFood por tenant
-- (no MVP usamos o app de teste único, mas estrutura suporta vários)
-- =============================================================================
create table public.ifood_credentials (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.tenants(id) on delete cascade,
    app_name text not null,
    client_id text not null,
    client_secret_encrypted text not null, -- cifrado com Fernet pela app
    environment text not null default 'TEST' check (environment in ('TEST', 'PRODUCTION')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (tenant_id, client_id)
);

-- =============================================================================
-- 4. MERCHANTS — lojas iFood vinculadas a um tenant
-- =============================================================================
create table public.merchants (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.tenants(id) on delete cascade,
    ifood_merchant_id text not null,        -- UUID do iFood (ex: e046a898-...)
    name text not null,
    corporate_name text,
    cnpj text,
    status text not null default 'active' check (status in ('active', 'inactive')),
    raw_data jsonb,                          -- snapshot completo do GET /merchants/{id}
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (tenant_id, ifood_merchant_id)
);

create index idx_merchants_tenant on public.merchants(tenant_id);
create index idx_merchants_ifood_id on public.merchants(ifood_merchant_id);

-- =============================================================================
-- 5. ORDERS — pedidos sincronizados da API iFood
-- =============================================================================
create table public.orders (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.tenants(id) on delete cascade,
    merchant_id uuid not null references public.merchants(id) on delete cascade,
    ifood_order_id text not null,
    display_id text,                         -- número curto do pedido (ex: "ABC1")
    status text not null,                    -- PLACED, CONFIRMED, DISPATCHED, CONCLUDED, CANCELLED
    order_type text,                         -- DELIVERY, TAKEOUT, INDOOR
    created_at_ifood timestamptz,            -- timestamp do iFood (createdAt)
    total_amount numeric(12, 2),
    customer_name text,
    raw_data jsonb not null,                 -- payload completo do GET /orders/{id}
    synced_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (tenant_id, ifood_order_id)
);

create index idx_orders_tenant on public.orders(tenant_id);
create index idx_orders_merchant on public.orders(merchant_id);
create index idx_orders_status on public.orders(status);
create index idx_orders_created_ifood on public.orders(created_at_ifood desc);

-- =============================================================================
-- 6. ORDER_EVENTS — eventos brutos do polling iFood (auditoria)
-- =============================================================================
create table public.order_events (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.tenants(id) on delete cascade,
    merchant_id uuid references public.merchants(id) on delete cascade,
    ifood_event_id text not null,
    ifood_order_id text,
    code text not null,                      -- PLC, CFM, DSP, CON, CAN, etc
    full_code text,                          -- código completo
    payload jsonb not null,
    acknowledged_at timestamptz,             -- quando enviamos /acknowledgment
    received_at timestamptz not null default now(),
    unique (ifood_event_id)
);

create index idx_order_events_tenant on public.order_events(tenant_id);
create index idx_order_events_order on public.order_events(ifood_order_id);
create index idx_order_events_received on public.order_events(received_at desc);

-- =============================================================================
-- 7. FINANCIAL_EVENTS — vendas, repasses, ocorrências financeiras
-- =============================================================================
create table public.financial_events (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.tenants(id) on delete cascade,
    merchant_id uuid not null references public.merchants(id) on delete cascade,
    ifood_reference_id text,                 -- ID do evento no iFood
    event_type text not null,                -- SALE, ANTICIPATION, OCCURRENCE, ADJUSTMENT
    competence_date date,                    -- data de competência (mês fiscal)
    amount numeric(12, 2) not null,
    description text,
    raw_data jsonb,
    synced_at timestamptz not null default now()
);

create index idx_financial_tenant on public.financial_events(tenant_id);
create index idx_financial_merchant on public.financial_events(merchant_id);
create index idx_financial_competence on public.financial_events(competence_date desc);
create index idx_financial_type on public.financial_events(event_type);

-- =============================================================================
-- 8. REVIEWS — avaliações dos clientes
-- =============================================================================
create table public.reviews (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.tenants(id) on delete cascade,
    merchant_id uuid not null references public.merchants(id) on delete cascade,
    ifood_review_id text not null,
    ifood_order_id text,
    score smallint check (score between 1 and 5),
    comment text,
    customer_name text,
    answered boolean not null default false,
    answer_text text,
    answered_at timestamptz,
    created_at_ifood timestamptz,
    raw_data jsonb,
    synced_at timestamptz not null default now(),
    unique (tenant_id, ifood_review_id)
);

create index idx_reviews_tenant on public.reviews(tenant_id);
create index idx_reviews_merchant on public.reviews(merchant_id);
create index idx_reviews_score on public.reviews(score);
create index idx_reviews_answered on public.reviews(answered);

-- =============================================================================
-- 9. SYNC_STATE — controle de sincronização (últimos timestamps por merchant)
-- =============================================================================
create table public.sync_state (
    tenant_id uuid not null references public.tenants(id) on delete cascade,
    merchant_id uuid not null references public.merchants(id) on delete cascade,
    domain text not null check (domain in ('orders', 'financial', 'reviews')),
    last_synced_at timestamptz,
    last_cursor text,                        -- pra paginação/cursor da API
    error_count int not null default 0,
    last_error text,
    primary key (tenant_id, merchant_id, domain)
);

-- =============================================================================
-- 10. TRIGGER: updated_at automático
-- =============================================================================
create or replace function public.set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger trg_tenants_updated before update on public.tenants
    for each row execute function public.set_updated_at();
create trigger trg_credentials_updated before update on public.ifood_credentials
    for each row execute function public.set_updated_at();
create trigger trg_merchants_updated before update on public.merchants
    for each row execute function public.set_updated_at();
create trigger trg_orders_updated before update on public.orders
    for each row execute function public.set_updated_at();

-- =============================================================================
-- 11. ROW LEVEL SECURITY (RLS) — isolar dados por tenant
-- =============================================================================
alter table public.tenants enable row level security;
alter table public.tenant_users enable row level security;
alter table public.ifood_credentials enable row level security;
alter table public.merchants enable row level security;
alter table public.orders enable row level security;
alter table public.order_events enable row level security;
alter table public.financial_events enable row level security;
alter table public.reviews enable row level security;
alter table public.sync_state enable row level security;

-- Helper: tenants do usuário logado
create or replace function public.user_tenant_ids()
returns setof uuid
language sql stable security definer
set search_path = public
as $$
    select tenant_id from public.tenant_users where user_id = auth.uid();
$$;

-- Policies genéricas: SELECT permitido se user está no tenant
create policy "tenants_select_own" on public.tenants
    for select using (id in (select public.user_tenant_ids()));

create policy "tenant_users_select_own" on public.tenant_users
    for select using (user_id = auth.uid() or tenant_id in (select public.user_tenant_ids()));

create policy "credentials_select_own" on public.ifood_credentials
    for select using (tenant_id in (select public.user_tenant_ids()));

create policy "merchants_select_own" on public.merchants
    for select using (tenant_id in (select public.user_tenant_ids()));

create policy "orders_select_own" on public.orders
    for select using (tenant_id in (select public.user_tenant_ids()));

create policy "order_events_select_own" on public.order_events
    for select using (tenant_id in (select public.user_tenant_ids()));

create policy "financial_select_own" on public.financial_events
    for select using (tenant_id in (select public.user_tenant_ids()));

create policy "reviews_select_own" on public.reviews
    for select using (tenant_id in (select public.user_tenant_ids()));

create policy "sync_state_select_own" on public.sync_state
    for select using (tenant_id in (select public.user_tenant_ids()));

-- INSERT/UPDATE/DELETE: backend usa service_role (bypassa RLS).
-- Não criamos policies de escrita pra usuários autenticados no MVP.
-- Em fase futura, criar policies role-based (admin/owner pode editar credentials, etc).

-- =============================================================================
-- 12. SEED — dados iniciais pro MVP
-- Tenant interno + merchant fictício do app de teste iFood.
-- =============================================================================
insert into public.tenants (id, name, slug)
values (
    '00000000-0000-0000-0000-000000000001',
    'gtrifood interno (TEST)',
    'gtrifood-test'
);

insert into public.merchants (tenant_id, ifood_merchant_id, name, corporate_name, cnpj, status)
values (
    '00000000-0000-0000-0000-000000000001',
    'e046a898-0625-4c65-b718-9c8e6c2c2923',
    'Teste - ACELERADORA GTR',
    'ACELERADORA GTR PARA RESTAURANTES GESTAO E CONSULTORIA DE DELIVERY LTDA',
    '99.999.999/9999-99',
    'active'
);
