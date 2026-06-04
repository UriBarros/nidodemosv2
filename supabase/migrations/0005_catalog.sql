-- =============================================================================
-- gtrifood — migration 0005: módulo Catalog (cardápio)
--
-- Espelha estrutura iFood Catalog API v2.0:
--   - Merchant tem 1+ catálogos (na prática quase sempre 1)
--   - Catálogo agrupa categorias
--   - Categoria agrupa itens
--   - Item tem nome, descrição, preço, status (AVAILABLE/UNAVAILABLE)
-- =============================================================================

-- =============================================================================
-- catalog_categories — categorias do cardápio
-- =============================================================================
create table public.catalog_categories (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.tenants(id) on delete cascade,
    merchant_id uuid not null references public.merchants(id) on delete cascade,
    ifood_catalog_id text not null,             -- ID do catálogo iFood (pai)
    ifood_category_id text not null,            -- ID da categoria no iFood
    name text not null,
    external_code text,                         -- código externo (opcional)
    status text not null default 'AVAILABLE',
    sequence int not null default 0,            -- ordem de exibição
    raw_data jsonb,
    synced_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (tenant_id, ifood_category_id)
);

create index idx_catalog_cat_tenant on public.catalog_categories(tenant_id);
create index idx_catalog_cat_merchant on public.catalog_categories(merchant_id);

create trigger trg_catalog_cat_updated before update on public.catalog_categories
    for each row execute function public.set_updated_at();

-- =============================================================================
-- catalog_items — itens do cardápio
-- =============================================================================
create table public.catalog_items (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.tenants(id) on delete cascade,
    merchant_id uuid not null references public.merchants(id) on delete cascade,
    category_id uuid references public.catalog_categories(id) on delete set null,
    ifood_item_id text not null,                -- ID do item no iFood
    ifood_product_id text,                      -- ID do produto-pai (catálogo mestre)
    name text not null,
    description text,
    external_code text,
    price numeric(12, 2),                       -- preço atual
    original_price numeric(12, 2),              -- preço sem desconto
    status text not null default 'AVAILABLE' check (
        status in ('AVAILABLE', 'UNAVAILABLE')
    ),
    image_path text,                            -- URL/caminho da imagem
    raw_data jsonb,                             -- payload completo do iFood
    synced_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (tenant_id, ifood_item_id)
);

create index idx_catalog_item_tenant on public.catalog_items(tenant_id);
create index idx_catalog_item_merchant on public.catalog_items(merchant_id);
create index idx_catalog_item_category on public.catalog_items(category_id);
create index idx_catalog_item_status on public.catalog_items(status);

create trigger trg_catalog_item_updated before update on public.catalog_items
    for each row execute function public.set_updated_at();

-- =============================================================================
-- RLS — members do tenant podem ler/escrever
-- =============================================================================
alter table public.catalog_categories enable row level security;
alter table public.catalog_items enable row level security;

create policy "catalog_cat_tenant_access" on public.catalog_categories
    for all
    using (
        tenant_id in (
            select tenant_id from public.tenant_users where user_id = auth.uid()
        )
    )
    with check (
        tenant_id in (
            select tenant_id from public.tenant_users where user_id = auth.uid()
        )
    );

create policy "catalog_item_tenant_access" on public.catalog_items
    for all
    using (
        tenant_id in (
            select tenant_id from public.tenant_users where user_id = auth.uid()
        )
    )
    with check (
        tenant_id in (
            select tenant_id from public.tenant_users where user_id = auth.uid()
        )
    );

comment on table public.catalog_categories is 'Categorias do cardápio sincronizadas do iFood (Catalog API v2.0).';
comment on table public.catalog_items is 'Itens do cardápio. Atualizações de preço/status propagam pro iFood via API.';
