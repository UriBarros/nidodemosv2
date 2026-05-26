# Rotina diária de desenvolvimento — gtrifood

Guia rápido pra subir o ambiente todo dia depois de ligar o PC.

## Pré-requisitos (só na primeira vez do PC)

- [Python 3.11+](https://www.python.org/downloads/) instalado
- [Git](https://git-scm.com/download/win) instalado
- VS Code (ou Cursor) instalado
- Repositório clonado em `E:\gtrifood`
- Arquivo `.env` preenchido (copia de `.env.example` e completa)
- Dependências instaladas:
  ```powershell
  cd E:\gtrifood
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  pip install -e ".[dev]"
  ```

## Toda vez que liga o PC

### 1. Abre o projeto no editor

VS Code → **File → Open Folder** → `E:\gtrifood`

### 2. Abre 3 terminais

`Ctrl + Shift + '` três vezes. Vai ter 3 abas embaixo (Terminal 1, 2, 3).

### 3. Ativa o venv em cada terminal

Em **cada um** dos 3:

```powershell
.venv\Scripts\Activate.ps1
```

Confirma que aparece `(.venv)` no prompt.

> **Erro `Activate.ps1 não pode ser carregado`?** Só na primeira vez do PC, roda:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

### 4. Sobe os 3 serviços (um por terminal)

**Terminal 1 — Worker (captura eventos iFood):**
```powershell
python scripts/run_poller.py
```

**Terminal 2 — API REST:**
```powershell
uvicorn gtrifood.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 3 — Frontend Next.js:**
```powershell
cd web
npm install   # primeira vez só
npm run dev
```

Abre: http://localhost:3000

### 5. Usa o sistema

Login com sua conta → dashboard Next.js funciona.

## Pra parar no fim do dia

Em cada terminal: `Ctrl + C`. Daí pode fechar VS Code e desligar PC.

## Atalho com Docker (opcional)

Se instalar Docker Desktop:

```powershell
docker compose up -d        # sobe tudo em background
docker compose logs -f      # acompanha logs (Ctrl+C pra sair, containers continuam)
docker compose down         # para tudo
```

## Comandos úteis

```powershell
# Atualiza dependências (depois de git pull com mudanças no pyproject.toml)
pip install -e ".[dev]"

# Status do git
git status

# Puxa atualizações remotas
git pull

# Salva e envia mudanças locais
git add -A
git commit -m "descrição da mudança"
git push
```

## Estrutura do projeto

```
E:\gtrifood\
├── .env                  ← suas credenciais (NUNCA commitar)
├── .env.example          ← template
├── pyproject.toml        ← dependências Python
├── docker-compose.yml    ← stack Docker
├── Dockerfile
├── Makefile              ← atalhos
├── src/gtrifood/         ← código backend
│   ├── api/              ← FastAPI app
│   ├── core/             ← db, security, auth, logging
│   ├── integrations/     ← cliente iFood
│   ├── models/           ← SQLAlchemy models
│   ├── services/         ← lógica de sync
│   └── workers/          ← poller de eventos
├── web/                  ← Next.js 14 frontend
│   ├── app/              ← App Router (login, dashboard, legal)
│   ├── components/       ← shadcn + custom (sidebar, KPI cards)
│   └── lib/              ← supabase client, api wrapper
├── scripts/              ← scripts utilitários
├── supabase/migrations/  ← SQL do banco
└── docs/                 ← documentação interna
```

## Em caso de erro

1. **Algo não inicia:** confere se o venv tá ativo `(.venv)` no prompt
2. **`ModuleNotFoundError`:** roda `pip install -e ".[dev]"` de novo
3. **Pedidos novos não aparecem:** confere se o worker (terminal 1) tá rodando
4. **Dashboard diz "API offline":** confere se a API (terminal 2) tá rodando
5. **Erro de banco/timed out:** reinicia o uvicorn (Ctrl+C + rerun no terminal 2)
6. **Logs de erro:** olha o terminal do uvicorn — traceback completo aparece lá

## Quando me chamar de novo

Roda `claude` (ou abre Claude Code) na pasta `E:\gtrifood`. Eu lembro do projeto pelas memórias.
