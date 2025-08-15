# gopilot

Bem-vindo ao projeto `gopilot`! Este projeto implementa um ecossistema de IA multi-agente sofisticado, baseado em uma arquitetura de microsserviços poliglota.

## Visão Geral da Arquitetura

O sistema é composto por vários serviços independentes que se comunicam por uma rede, orquestrados por um sistema de agentes central. Os componentes principais incluem:

- **LibreChat:** A principal interface web para o usuário.
- **Orchestrator:** O "cérebro" em Python que processa os pedidos e delega tarefas.
- **Servidores de Ferramentas:** Um conjunto de microsserviços especializados que fornecem capacidades para:
  - Acesso a banco de dados (`genai-toolbox` em Go)
  - Mídia Generativa (`mcp-genmedia`, `veo-app` em Python)
  - Assistência de Código (`codemcp` em Python)
  - Memória Cognitiva (`cognee-service` em Python)

Para um detalhamento completo de todos os componentes e suas relações, por favor, consulte o nosso [Grafo de Conhecimento do Projeto](./docs/knowledge_graph.md).

---

## Como Começar

Siga estas instruções para executar todo o ecossistema `gopilot` em sua máquina local.

### Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Setup

1.  **Configure as Variáveis de Ambiente:**
    Crie seu arquivo de configuração de ambiente local copiando o exemplo:
    ```bash
    cp .env.example .env
    ```
    Agora, abra o arquivo `.env` e edite as variáveis conforme necessário. No mínimo, você deve substituir os valores de placeholder para segredos como `JWT_SECRET`.

2.  **Construa e Execute a Aplicação:**
    Assim que seu arquivo `.env` estiver configurado, você pode construir e iniciar todos os serviços com um único comando:
    ```bash
    docker-compose up --build
    ```
    A flag `--build` irá construir as imagens Docker na primeira vez. Inícios subsequentes podem omitir esta flag (`docker-compose up`), a menos que você faça alterações nos Dockerfiles ou no código da aplicação.

    O build inicial pode levar vários minutos, pois ele baixará as imagens base e instalará todas as dependências para todos os serviços.

---

## Visão Geral dos Serviços

Uma vez em execução, os seguintes serviços estarão disponíveis:

| Serviço | Porta Local | Descrição |
|---|---|---|
| **LibreChat** | `3080` | A interface web principal. Acesse na porta `3080` do seu host Docker. |
| **Orchestrator** | `8001` | O endpoint da API principal para o orquestrador de agentes. |
| **genai-toolbox** | `8081` | O servidor de ferramentas de banco de dados. |
| **cognee-service** | `8002` | O serviço de memória cognitiva. |
