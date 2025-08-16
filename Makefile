SHELL := /bin/bash

.PHONY: help bootstrap env-init deps up down ps logs test lint fmt

help:
	@echo "Targets:"
	@echo "  bootstrap     - Copia .env.example se .env não existir e gera segredos"
	@echo "  env-init      - Gera JWT_SECRET/JWT_REFRESH_SECRET se vazios"
	@echo "  deps          - Instala dependências por serviço (uv/npm/go)"
	@echo "  up            - Sobe toda a stack (docker-compose up --build)"
	@echo "  down          - Derruba a stack"
	@echo "  ps            - Lista serviços"
	@echo "  logs          - Logs agregados"
	@echo "  test          - Roda testes por serviço"
	@echo "  lint          - Lint básico por serviço"
	@echo "  set-endpoint-global    - Aponta para endpoint global do Vertex"
	@echo "  set-endpoint-dedicated - Aponta para endpoint dedicado do Vertex"
	@echo "  run-orchestrator TOKEN=... - Sobe orchestrator com token inline"
	@echo "  run-librechat          - Sobe LibreChat"
	@echo "  show-ip                - Mostra IP da VM"
	@echo "  set-domain IP=...      - Define DOMAIN_CLIENT/DOMAIN_SERVER para o IP"

bootstrap:
	@if [ ! -f .env ]; then cp .env.example .env; echo "Copiado .env.example -> .env"; fi
	@$(MAKE) env-init

env-init:
	@if grep -q '^JWT_SECRET=""' .env; then \
	  sed -i "s/^JWT_SECRET=\"\"/JWT_SECRET=$$(openssl rand -hex 32)/" .env; \
	  echo "JWT_SECRET gerado"; \
	fi
	@if grep -q '^JWT_REFRESH_SECRET=""' .env; then \
	  sed -i "s/^JWT_REFRESH_SECRET=\"\"/JWT_REFRESH_SECRET=$$(openssl rand -hex 32)/" .env; \
	  echo "JWT_REFRESH_SECRET gerado"; \
	fi

deps:
	@echo "[fast-agent] uv sync" && cd fast-agent && uv sync --all-extras || exit 1
	@echo "[fastmcp] uv sync" && cd fastmcp && uv sync --all-extras || exit 1
	@echo "[codemcp] uv sync" && cd codemcp && uv sync --all-extras || exit 1
	@echo "[cognee] uv sync" && cd cognee && uv sync --all-extras || exit 1
	@echo "[genai-toolbox] go mod download" && cd genai-toolbox && go mod download || exit 1
	@echo "[LibreChat] npm ci" && cd LibreChat && npm ci || exit 1

up:
	docker-compose up --build

down:
	docker-compose down

ps:
	docker-compose ps

logs:
	docker-compose logs -f --tail=200

test:
	@echo "[fast-agent] pytest" && cd fast-agent && uv run pytest -q || exit 1
	@echo "[codemcp] pytest" && cd codemcp && uv run pytest -q || exit 1
	@echo "[genai-toolbox] go test" && cd genai-toolbox && go test ./... || exit 1
	@echo "[LibreChat] client/api tests" && cd LibreChat && npm run test:client && npm run test:api || exit 1

lint:
	@echo "[fast-agent] ruff" && cd fast-agent && uv run ruff check . || exit 1
	@echo "[codemcp] ruff" && cd codemcp && uv run ruff check . || exit 1
	@echo "[genai-toolbox] go fmt/vet" && cd genai-toolbox && go fmt ./... && go vet ./... || exit 1
	@echo "[LibreChat] eslint" && cd LibreChat && npm run lint || exit 1

set-endpoint-global:
	@sed -i 's#^UPSTREAM_CHAT_COMPLETIONS_URL=.*#UPSTREAM_CHAT_COMPLETIONS_URL=https://us-east5-aiplatform.googleapis.com/v1/projects/764370180968/locations/us-east5/endpoints/openapi/chat/completions#' .env && echo "Endpoint global configurado"

set-endpoint-dedicated:
	@sed -i 's#^UPSTREAM_CHAT_COMPLETIONS_URL=.*#UPSTREAM_CHAT_COMPLETIONS_URL=https://5040565922004205568.us-east5-764370180968.prediction.vertexai.goog/openapi/chat/completions#' .env && echo "Endpoint dedicado configurado"

run-orchestrator:
	@if [ -z "$(TOKEN)" ]; then echo "Uso: make run-orchestrator TOKEN=..."; exit 1; fi
	GOOGLE_ACCESS_TOKEN='$(TOKEN)' docker compose up -d orchestrator
	@docker compose ps

run-librechat:
	docker compose up -d librechat

show-ip:
	@VM_IP=$$(hostname -I | awk '{print $$1}'); echo $$VM_IP

set-domain:
	@if [ -z "$(IP)" ]; then echo "Uso: make set-domain IP=SEU_IP"; exit 1; fi
	@grep -q '^DOMAIN_CLIENT=' .env && sed -i 's#^DOMAIN_CLIENT=.*#DOMAIN_CLIENT=http://$(IP):3080#' .env || echo 'DOMAIN_CLIENT=http://$(IP):3080' >> .env
	@grep -q '^DOMAIN_SERVER=' .env && sed -i 's#^DOMAIN_SERVER=.*#DOMAIN_SERVER=http://$(IP):3080#' .env || echo 'DOMAIN_SERVER=http://$(IP):3080' >> .env
	@echo "DOMAIN_CLIENT/DOMAIN_SERVER configurados para http://$(IP):3080"
