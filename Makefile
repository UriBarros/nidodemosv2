.PHONY: help install dev-api dev-worker dev-dashboard docker-build up down logs ps restart-api restart-worker restart-dashboard fmt lint test

help:
	@echo "gtrifood — Makefile"
	@echo ""
	@echo "Dev local (sem Docker):"
	@echo "  make install              instala deps no venv"
	@echo "  make dev-api              roda FastAPI com --reload"
	@echo "  make dev-worker           roda worker de polling"
	@echo "  make dev-dashboard        roda Streamlit"
	@echo ""
	@echo "Docker / produção:"
	@echo "  make docker-build         build da imagem"
	@echo "  make up                   sobe api+worker+dashboard em background"
	@echo "  make down                 para tudo"
	@echo "  make logs                 follow logs (Ctrl+C pra sair)"
	@echo "  make ps                   status dos containers"
	@echo "  make restart-api          reinicia só a api"
	@echo "  make restart-worker       reinicia só o worker"
	@echo "  make restart-dashboard    reinicia só o dashboard"
	@echo ""
	@echo "Qualidade:"
	@echo "  make fmt                  formata com ruff"
	@echo "  make lint                 lint com ruff + mypy"
	@echo "  make test                 pytest"

install:
	pip install -e ".[dev]"

dev-api:
	uvicorn gtrifood.api.main:app --reload --host 0.0.0.0 --port 8000

dev-worker:
	python scripts/run_poller.py

dev-dashboard:
	streamlit run dashboard/app.py

docker-build:
	docker compose build

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

restart-api:
	docker compose restart api

restart-worker:
	docker compose restart worker

restart-dashboard:
	docker compose restart dashboard

fmt:
	ruff format src dashboard scripts

lint:
	ruff check src dashboard scripts
	mypy src

test:
	pytest
