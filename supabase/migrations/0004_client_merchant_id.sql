-- =============================================================================
-- gtrifood — migration 0004: ifood_merchant_id no client
--
-- UX EneWay-like: operador cola ID do merchant iFood ao cadastrar cliente.
-- Após autorização via userCode, o backend faz sync do merchant específico.
-- =============================================================================

alter table public.clients
    add column ifood_merchant_id text;

comment on column public.clients.ifood_merchant_id is
    'ID do merchant iFood (UUID) — informado pelo operador no cadastro. '
    'Após autorização, vincula automaticamente o merchant a este client.';

create index idx_clients_ifood_merchant on public.clients(ifood_merchant_id);
