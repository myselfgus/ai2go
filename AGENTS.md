# Repository Guidelines

## Estrutura do Projeto
- Serviços: `fast-agent/` (orquestrador e agentes), `codemcp/` (MCP para arquivos/código), `genai-toolbox/` (MCP para bancos de dados em Go), `cognee/` (memória/knowledge graph), `LibreChat/` (UI web). Orquestração em `docker-compose.yml`. Veja `docs/knowledge_graph.md`.
- Testes: por linguagem em cada serviço (`fast-agent/tests/{unit,integration,e2e}`, `LibreChat/e2e`, `genai-toolbox/tests`).
- Configuração: `.env` na raiz (copiar de `.env.example`), e arquivos por serviço (`pyproject.toml`, `go.mod`, `package.json`).

## Build, Teste e Desenvolvimento
- Stack completo: `cp .env.example .env && docker-compose up --build`.
- Fast Agent: `cd fast-agent && uv run pytest -q` | lint: `uv run ruff check .`.
- CodeMCP: `cd codemcp && uv run pytest -q` | type-check: `uv run pyright`.
- GenAI Toolbox (Go): `cd genai-toolbox && go test ./... && go build ./...`.
- LibreChat (Node): `cd LibreChat && npm ci && npm run frontend:dev` (build: `npm run frontend`).
Obs.: Python usa `uv` (instale via docs.astral.sh). Consulte os READMEs de cada serviço.

## Estilo e Nomenclatura
- Python: indentação 4 espaços; `ruff` ativo (ex.: 100 col. em `fast-agent`, 88 em `codemcp`). `snake_case` p/ funções, `PascalCase` p/ classes.
- Go: `gofmt`/`golangci-lint`; pacotes minúsculos, sem `_`.
- Node/TS: ESLint + Prettier no `LibreChat`; 2 espaços; componentes React em `PascalCase`.

## Testes
- Python: `pytest` (+ `pytest-asyncio`); arquivos `test_*.py`; use marcadores existentes (`unit`, `integration`, `e2e`).
- Go: `*_test.go` com `go test ./...`.
- Web: Playwright/Jest (`npm run e2e`, `npm run test:client`). Cobrir lógica nova e atualizar e2e ao alterar APIs/UI.

## Commits e Pull Requests
- Commits: imperativo curto (ex.: `feat(orchestrator): roteia tarefas via MCP`), referencie issues (`Closes #123`).
- PRs: descrição clara, escopo, evidências de teste (logs/prints), docs e `.env.example` atualizados; linters e testes verdes nos serviços afetados.

## Arquitetura e Containers
- Orquestrador (`fast-agent`) coordena agentes e fala MCP com: `codemcp`, `genai-toolbox`, `cognee-mcp`, `mcp-genmedia`, e ponte `a2a-mcp-server` (ver knowledge graph).
- “Obras” (repositórios) podem ser montadas como volumes por container. Padrão: `/workspace` por obra; evite secrets no volume.
- Modelos: pode usar GPT-OSS/OpenAI/Vertex via configs do `fast-agent`. Ports padrão: UI `3080`, orquestrador `8001`, DB tools `8081`, cognee `8002`.

## Políticas Rígidas
- PROIBIDO LOCALHOST, PROIBIDO MOCK, PROIBIDO PLACEHOLDER.
- Qualquer senha/secret/token: pare, solicite ao maintainer e só então atualize `.env`/configs. Nunca commitar segredos.
