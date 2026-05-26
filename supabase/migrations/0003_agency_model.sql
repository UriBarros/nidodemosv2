-- =============================================================================
-- gtrifood — migration 0003: modelo agência (clients + userCode flow)
--
-- Pivot do modelo de SaaS multi-tenant pra agência:
--   - 1 tenant fixo = Aceleradora GTR
--   - users do tenant = você + equipe (acessam o painel)
--   - clients = lojistas iFood gerenciados pela agência (NUNCA logam)
--   - cada client tem refresh_token próprio via userCode flow
--   - merchants vinculam-se a um client (1 client → N merchants)
--
-- LGPD: refresh_token cifrado com Fernet antes de salvar (ENCRYPTION_KEY).
-- =============================================================================

-- =============================================================================
-- 1. CLIENTS — lojistas gerenciados pela agência
-- =============================================================================
create table public.clients (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.tenants(id) on delete cascade,
    name text not null,                          -- "Pizzaria do Zé"
    legal_name text,                             -- razão social
    cnpj text,
    phone text,
    email text,
    notes text,                                  -- observações internas da agência
    status text not null default 'pending' check (
        status in ('pending', 'connected', 'disconnected', 'error')
    ),
    -- Tokens userCode (cifrados com Fernet pela app)
    refresh_token_encrypted text,
    access_token_encrypted text,
    token_expires_at timestamptz,
    token_scope text,                            -- ex: "merchant,order,financial,review"
    -- Auditoria
    connected_at timestamptz,                    -- quando completou userCode flow
    disconnected_at timestamptz,
    last_error text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_clients_tenant on public.clients(tenant_id);
create index idx_clients_status on public.clients(status);

create trigger trg_clients_updated before update on public.clients
    for each row execute function public.set_updated_at();

comment on table public.clients is 'Lojistas iFood gerenciados pela agência. Nunca logam — só fornecem userCode.';

-- =============================================================================
-- 2. MERCHANTS — vincular a um client (1 client → N merchants/unidades)
-- =============================================================================
alter table public.merchants
    add column client_id uuid references public.clients(id) on delete cascade;

create index idx_merchants_client on public.merchants(client_id);

-- =============================================================================
-- 3. USER_CODE_SESSIONS — rastreia sessões de userCode em andamento
-- =============================================================================
create table public.user_code_sessions (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.tenants(id) on delete cascade,
    client_id uuid references public.clients(id) on delete cascade,
    user_code text not null,                     -- ex: "ABC123"
    verification_url text not null,              -- portal.ifood.com.br/...
    verification_url_complete text,              -- URL completa com code
    authorization_code_verifier text,            -- pra trocar por token
    expires_at timestamptz not null,             -- ~10min de validade no iFood
    status text not null default 'pending' check (
        status in ('pending', 'authorized', 'expired', 'error')
    ),
    last_polled_at timestamptz,
    poll_count int not null default 0,
    last_error text,
    created_at timestamptz not null default now(),
    completed_at timestamptz
);

create index idx_user_code_sessions_tenant on public.user_code_sessions(tenant_id);
create index idx_user_code_sessions_client on public.user_code_sessions(client_id);
create index idx_user_code_sessions_status on public.user_code_sessions(status);

comment on table public.user_code_sessions is 'Sessões temporárias do userCode flow do iFood. Expira em ~10min.';

-- =============================================================================
-- 4. RLS pra novas tabelas
-- =============================================================================
alter table public.clients enable row level security;
alter table public.user_code_sessions enable row level security;

-- Clients: members do tenant podem ler/criar/atualizar
create policy "clients_tenant_access" on public.clients
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

-- user_code_sessions: idem
create policy "user_code_sessions_tenant_access" on public.user_code_sessions
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

-- =============================================================================
-- 5. DESATIVAR trigger de auto-create-tenant (modelo agência)
-- =============================================================================
-- Antes: cada signup criava tenant novo (SaaS B2B).
-- Agora: novos signups NÃO criam tenant. Admin convida users no tenant existente.
drop trigger if exists on_auth_user_created on auth.users;

-- Função fica disponível pra reativar futuramente se virar SaaS multi-org.
-- Não dropamos public.handle_new_user() pra manter histórico.

-- =============================================================================
-- 6. BACKFILL: cria 1 client default pra cada tenant existente
--    e vincula merchants existentes
-- =============================================================================
do $$
declare
    t record;
    new_client_id uuid;
    merchant_count int;
begin
    for t in select id, name from public.tenants loop
        -- Conta merchants do tenant
        select count(*) into merchant_count
        from public.merchants where tenant_id = t.id;

        if merchant_count > 0 then
            -- Cria client placeholder pra agrupar merchants existentes
            insert into public.clients (tenant_id, name, status, notes)
            values (
                t.id,
                'Cliente legado — ' || t.name,
                'connected',
                'Auto-criado pela migration 0003. Editar nome/CNPJ/telefone pra dados reais.'
            )
            returning id into new_client_id;

            -- Vincula merchants do tenant ao client recém-criado
            update public.merchants
            set client_id = new_client_id
            where tenant_id = t.id and client_id is null;

            raise notice 'Tenant % (%): % merchants migrados pro client %',
                t.id, t.name, merchant_count, new_client_id;
        end if;
    end loop;
end $$;

-- =============================================================================
-- 7. (opcional) Forçar merchants.client_id NOT NULL após backfill
-- =============================================================================
-- Comentado por enquanto pra permitir merchants sem client (ex: importação inicial).
-- Descomentar em migration futura quando workflow estiver maduro:
-- alter table public.merchants alter column client_id set not null;
