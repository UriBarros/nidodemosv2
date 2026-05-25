# Deploy via Portainer + Traefik + GitHub Actions

Guia passo-a-passo pra subir o gtrifood na VPS usando o fluxo:

```
push GitHub main → Actions builda imagem → push GHCR
              → webhook Portainer → stack faz pull + redeploy
```

## Pré-requisitos confirmados

- VPS Hostinger Ubuntu 22.04 com Docker Swarm + Portainer
- Stack `traefik` rodando com certresolver `letsencrypt` e entrypoint `websecure`
- Rede overlay `network_public` compartilhada com Traefik
- Domínio: `gtrifood.aceleradoragtr.cloud` (CNAME → automacao)
- Repo GitHub: `https://github.com/UriBarros/nidodemosv2`

## 1. Tornar imagem GHCR pública (uma vez)

Após o primeiro push do GitHub Actions, o pacote vai aparecer em:
`https://github.com/UriBarros?tab=packages`

1. Clica no pacote `nidodemosv2`
2. **Package settings** (canto direito)
3. **Change visibility** → **Public** → confirma com o nome do pacote
4. Salva

Isso permite o Portainer puxar a imagem sem autenticar.

> **Se quiser manter privado:** no Portainer → Registries → Add registry → GitHub → cria PAT (Personal Access Token) com escopo `read:packages`. Mais trabalho. Pra MVP, deixa público.

## 2. Aplicar migrations no Supabase (se ainda não fez)

SQL Editor do Supabase → roda `supabase/migrations/0001_init.sql` (se for projeto novo) e `supabase/migrations/0002_auth_trigger.sql`.

Se já está aplicado em dev, **pula** — o banco é o mesmo (mesma instância Supabase pra dev e prod no MVP).

## 3. Criar stack no Portainer

1. Portainer → menu lateral **Stacks** → **Add stack**
2. Nome: `gtrifood`
3. **Build method**: **Repository**
4. Preencher:
   - **Repository URL**: `https://github.com/UriBarros/nidodemosv2`
   - **Repository reference**: `refs/heads/main`
   - **Compose path**: `deploy/portainer-stack.yml`
   - **Authentication**: desligado (repo público)
   - **Automatic updates**: **Enable**
   - **Mechanism**: **Webhook** → Portainer gera uma URL única, **copia ela**
   - **Polling interval**: desligado (vamos usar só webhook)

## 4. Configurar variáveis de ambiente

Rola até a seção **Environment variables** → **Advanced mode** → cola TODAS as variáveis abaixo, uma por linha. Substitui valores pelos do seu `.env` local:

```
IFOOD_CLIENT_ID=xxx
IFOOD_CLIENT_SECRET=xxx
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
SUPABASE_JWT_SECRET=
DATABASE_URL=postgresql://postgres.xxx:senha%40encoded@aws-1-sa-east-1.pooler.supabase.com:6543/postgres
ENCRYPTION_KEY=xxx=
LOG_LEVEL=INFO
```

> `SUPABASE_JWT_SECRET` fica vazio (usamos ES256 via JWKS).

> `DATABASE_URL` **precisa ter a senha URL-encoded** (`@` → `%40`, etc).

5. **Deploy the stack** (botão azul no fim)

Portainer faz:
1. Clona o repo
2. Pull da imagem `ghcr.io/uribarros/nidodemosv2:latest` (se não existir, falha — precisa do primeiro Actions ter rodado antes)
3. Sobe os 3 serviços (api, worker, dashboard)
4. Traefik detecta os labels → gera cert SSL Let's Encrypt → roteia

## 5. Configurar GitHub Secret pra webhook

No GitHub:

1. Repo `nidodemosv2` → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret**
3. **Name**: `PORTAINER_WEBHOOK_URL`
4. **Value**: cola a URL do webhook que copiou no passo 3
5. **Add secret**

A partir do próximo push em `main`, Actions builda imagem, faz push, e dispara o webhook → Portainer faz pull + redeploy automático.

## 6. Primeiro push pra testar

No seu PC:

```powershell
cd E:\gtrifood
git add -A
git commit -m "feat: add CI/CD + Portainer stack"
git push
```

Acompanha em:
- **GitHub Actions**: https://github.com/UriBarros/nidodemosv2/actions (build ~3min)
- **Portainer**: stack `gtrifood` → ver containers subindo

Quando Actions concluir + webhook disparar, Portainer atualiza. Após 1-2min, acesse:

- **Dashboard**: https://gtrifood.aceleradoragtr.cloud
- **API Swagger**: https://gtrifood.aceleradoragtr.cloud/api/docs
- **Healthcheck**: https://gtrifood.aceleradoragtr.cloud/api/health

## 7. Verificar SSL

Primeiro acesso pode demorar 30-60s pro Traefik emitir o cert Let's Encrypt. Cadeado verde no navegador = OK.

Se ficar **"site não seguro"**:
- Verifica logs do Traefik no Portainer (Services → traefik → Logs)
- Procura por `gtrifood.aceleradoragtr.cloud` — vai mostrar erro se houver
- Comum: DNS ainda não propagado (espera mais 5min)

## 8. Fluxo de atualização daqui em diante

```
1. Edita código no seu PC
2. git push
3. Aguarda GitHub Actions (~3min)
4. Portainer recebe webhook → pull imagem nova → redeploy
5. ~1min depois, mudança no ar
```

Nenhuma ação manual no servidor.

## Troubleshooting

### `image not found` no Portainer

GitHub Actions ainda não rodou (ou falhou). Roda manualmente:
GitHub → Actions → workflow `build-and-push` → **Run workflow** → branch main.

### Container reinicia em loop

Portainer → Stack `gtrifood` → clica no serviço com erro → **Logs**. Geralmente é env var faltando ou DATABASE_URL incorreto.

### Dashboard mostra "API offline"

Verifica `API_BASE_URL` no env do dashboard. Deve ser `https://gtrifood.aceleradoragtr.cloud/api`.

### Webhook não dispara

Confere GitHub Secret `PORTAINER_WEBHOOK_URL`. Pode testar manual: `curl -X POST <URL>`.

### Migrations precisam ser atualizadas

Não tem auto-migration ainda. Pra cada nova migration, aplica manualmente no SQL Editor do Supabase.

## Custos previstos

- VPS Hostinger KVM 2: já paga
- Domínio aceleradoragtr.cloud: já paga
- Supabase Free tier: 0 (até bater limites)
- GHCR pública: 0
- GitHub Actions: 2000 min/mês free pra repos públicos

**Total adicional: R$ 0** enquanto MVP.
