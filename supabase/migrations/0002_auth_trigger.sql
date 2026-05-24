-- =============================================================================
-- gtrifood — migration 0002: trigger de auto-onboarding de tenant ao signup
--
-- Quando um usuário se cadastra no Supabase Auth (auth.users), automaticamente:
--   1. Cria um tenant novo (slug derivado do email)
--   2. Cria tenant_users vinculando o novo user ao tenant com role=owner
--
-- Modelo: 1 user = 1 tenant inicial (B2B SaaS).
-- Depois, o owner pode convidar membros pro mesmo tenant (fase futura).
-- =============================================================================

-- Helper: gera slug a partir do email (parte antes do @, sanitizado)
create or replace function public.slugify_email(email text)
returns text
language sql
immutable
as $$
    select regexp_replace(
        lower(split_part(email, '@', 1)),
        '[^a-z0-9]+',
        '-',
        'g'
    );
$$;

-- Trigger function: roda DEPOIS de inserir em auth.users
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
    base_slug text;
    unique_slug text;
    suffix int := 0;
    new_tenant_id uuid;
begin
    base_slug := public.slugify_email(new.email);
    unique_slug := base_slug;

    -- Garante slug único (em caso de colisão, anexa -1, -2, ...)
    while exists (select 1 from public.tenants where slug = unique_slug) loop
        suffix := suffix + 1;
        unique_slug := base_slug || '-' || suffix::text;
    end loop;

    -- Cria tenant
    insert into public.tenants (name, slug)
    values (
        coalesce(new.raw_user_meta_data->>'full_name', new.email),
        unique_slug
    )
    returning id into new_tenant_id;

    -- Vincula user ao tenant como owner
    insert into public.tenant_users (tenant_id, user_id, role)
    values (new_tenant_id, new.id, 'owner');

    return new;
end;
$$;

-- Registra trigger
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- =============================================================================
-- Policies de escrita pra usuários autenticados
-- (no MVP só permitimos leitura — agora liberamos INSERT em alguns lugares)
-- =============================================================================

-- ifood_credentials: owner/admin pode criar/atualizar
create policy "credentials_modify_owner" on public.ifood_credentials
    for all
    using (
        tenant_id in (
            select tenant_id from public.tenant_users
            where user_id = auth.uid() and role in ('owner', 'admin')
        )
    )
    with check (
        tenant_id in (
            select tenant_id from public.tenant_users
            where user_id = auth.uid() and role in ('owner', 'admin')
        )
    );
