# Deploy gtrifood em VPS — Ubuntu + Docker + nginx + Let's Encrypt

Guia passo-a-passo pra subir o gtrifood em um VPS Ubuntu (testado em 22.04 LTS) com domínio HTTPS válido.

**Pré-requisitos:**
- VPS rodando Ubuntu 22.04+ (Hetzner CX11, DigitalOcean Basic, Vultr High Frequency, etc — qualquer 1GB RAM serve)
- Domínio próprio com acesso ao painel DNS (Registro.br, Cloudflare, etc)
- Cliente SSH local (PowerShell, WSL, ou PuTTY)

> Para o restante deste guia, troque:
> - `gtrifood.seudominio.com.br` → seu domínio real
> - `IP_DO_SEU_VPS` → IP público do VPS
> - `seu_usuario` → username Linux que você vai criar (ex: `deploy`)

---

## 1. Conectar e preparar o VPS

### 1.1 SSH inicial como root

```bash
ssh root@IP_DO_SEU_VPS
```

### 1.2 Atualizar pacotes

```bash
apt update && apt upgrade -y
```

### 1.3 Criar usuário não-root

```bash
adduser seu_usuario              # define senha forte
usermod -aG sudo seu_usuario
```

### 1.4 Copiar sua chave SSH pro novo usuário (do seu PC local)

No PC local:
```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh seu_usuario@IP_DO_SEU_VPS "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

> Se não tem chave SSH: gera com `ssh-keygen -t ed25519` antes.

### 1.5 Desabilitar login de root e password (no VPS, como root)

```bash
sudo nano /etc/ssh/sshd_config
```

Garantir:
```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

Salva → reinicia SSH:
```bash
systemctl restart sshd
```

A partir de agora, login só como `seu_usuario` via chave SSH.

### 1.6 Firewall (UFW)

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

---

## 2. Instalar Docker + Docker Compose

```bash
# Docker oficial
curl -fsSL https://get.docker.com | sudo sh

# Adiciona seu user ao grupo docker (logout/login depois)
sudo usermod -aG docker seu_usuario

# Verifica
docker --version
docker compose version
```

Faz **logout e login de novo** pra ativar permissão de grupo.

---

## 3. Configurar DNS

No painel do seu registrador de domínio (Cloudflare, Registro.br, etc), cria:

| Tipo | Nome             | Valor                  | TTL  |
|------|------------------|------------------------|------|
| A    | `gtrifood`       | `IP_DO_SEU_VPS`        | 300  |

Aguarda 5-15min pra propagar. Verifica:
```bash
dig +short gtrifood.seudominio.com.br
# deve retornar IP_DO_SEU_VPS
```

---

## 4. Clonar repo e configurar `.env`

```bash
cd ~
git clone https://github.com/UriBarros/nidodemosv2.git gtrifood
cd gtrifood

# Cria .env (NÃO commitar)
cp .env.example .env
nano .env
```

Preenche:
- `IFOOD_CLIENT_ID`, `IFOOD_CLIENT_SECRET` — do app iFood
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` — do painel Supabase
- `DATABASE_URL` — connection string Supabase (encoded)
- `ENCRYPTION_KEY` — gera com:
  ```bash
  docker run --rm python:3.11-slim python -c "from secrets import token_urlsafe; import base64; print(base64.urlsafe_b64encode(token_urlsafe(32).encode()[:32]).decode())"
  ```

---

## 5. Subir os containers

```bash
docker compose up -d --build
docker compose ps
```

Esperado: `api`, `worker`, `dashboard` rodando.

Logs:
```bash
docker compose logs -f
```

Teste local (no VPS):
```bash
curl http://localhost:8000/health
# {"status":"ok","version":"0.1.0"}
```

---

## 6. nginx reverse proxy + SSL

### 6.1 Instalar nginx + certbot

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

### 6.2 Configurar nginx

```bash
sudo nano /etc/nginx/sites-available/gtrifood
```

Cola:

```nginx
server {
    listen 80;
    server_name gtrifood.seudominio.com.br;

    # Dashboard (Streamlit) na raiz
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # API REST sob /api (proxy_pass remove o /api ao encaminhar)
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Webhook do iFood (futuro)
    location /webhooks/ifood {
        proxy_pass http://127.0.0.1:8000/webhooks/ifood;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Habilita:
```bash
sudo ln -s /etc/nginx/sites-available/gtrifood /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t           # valida config
sudo systemctl reload nginx
```

Teste sem SSL: abre `http://gtrifood.seudominio.com.br` no navegador → dashboard deve aparecer.

### 6.3 Emitir certificado SSL via Let's Encrypt

```bash
sudo certbot --nginx -d gtrifood.seudominio.com.br
```

- Email pra notificações (use email real)
- Aceita termos
- Escolhe redirecionar HTTP → HTTPS

Renovação automática:
```bash
sudo systemctl status certbot.timer
# já ativa por padrão; certbot renova 60 dias antes de expirar
```

Teste: `https://gtrifood.seudominio.com.br` → dashboard com cadeado verde.

---

## 7. Auto-restart se VPS reiniciar

Docker já restart=unless-stopped no compose. Pra garantir Docker mesmo sobe no boot:

```bash
sudo systemctl enable docker
```

---

## 8. Atualizar (deploy de novas versões)

Quando empurrar nova versão no GitHub:

```bash
cd ~/gtrifood
git pull
docker compose up -d --build
```

Container reinicia com nova imagem. Worker continua de onde parou (poll baseado em time).

---

## 9. Logs e troubleshooting

```bash
# Tudo
docker compose logs -f

# Só um serviço
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f dashboard

# nginx
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Reiniciar um serviço
docker compose restart api
```

Container morrendo direto?
```bash
docker compose ps
docker compose logs api | tail -50
```

---

## 10. Backup (futuro)

Banco está no Supabase (já tem backups automáticos no plano Pro). `.env` é a única coisa crítica no VPS — guarda em local seguro (1Password, Bitwarden).

---

## Checklist final pré-homologação iFood

- [ ] `https://gtrifood.seudominio.com.br` responde com cadeado verde
- [ ] Dashboard carrega + login funciona
- [ ] Worker continua rodando após VPS reiniciar
- [ ] Logs sem erros recorrentes
- [ ] URL pública pronta pra ser informada ao iFood como webhook endpoint

Pronto pra criar app PRODUCTION no portal iFood e solicitar homologação.
