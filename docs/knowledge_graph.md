# Project Knowledge Graph

This document outlines the core entities and their relationships within the `gopilot` project ecosystem. It serves as the foundational memory for the `cognee` cognitive architecture.

## Ontology

- **Entities:** `Service`, `Component`, `Technology`, `Protocol`, `Class`, `File`
- **Relations:** `USES`, `CONTAINS`, `IMPLEMENTS`, `COMMUNICATES_WITH`, `IS_A`, `CONFIGURED_BY`, `SERVED_BY`

---

## Entities

### Services (High-Level Microservices)
- **ID:** `Service:Orchestrator`
- **ID:** `Service:LibreChat`
- **ID:** `Service:genai-toolbox`
- **ID:** `Service:cognee-mcp`
- **ID:** `Service:mcp-genmedia`
- **ID:** `Service:codemcp`
- **ID:** `Service:a2a-mcp-server`

### Components (Key Modules or Frameworks)
- **ID:** `Component:fast-agent`
- **ID:** `Component:fastmcp`
- **ID:** `Component:cognee`
- **ID:** `Component:codemcp`
- **ID:** `Component:genai-toolbox`
- **ID:** `Component:veo-app`

### Technologies & Protocols
- **ID:** `Technology:Python`
- **ID:** `Technology:Go`
- **ID:** `Technology:Docker`
- **ID:** `Technology:PostgreSQL`
- **ID:** `Technology:Neo4j`
- **ID:** `Technology:VertexAI`
- **ID:** `Protocol:MCP`
- **ID:** `Protocol:A2A`

---

## Detailed Component Analysis

### `Component:fast-agent`
A comprehensive framework for building and managing multi-agent AI applications. It is used to define the logic and workflows of agents. Agents built with `fast-agent` will be served as MCP microservices using the `fastmcp` framework.

- **Key Classes:**
  - `Class:FastAgent`: The main entrypoint and factory for creating agent applications.
  - `Class:MCPApp`: Manages the global application state and context.
  - `Class:Agent`: The fundamental agent unit that interacts with LLMs and tools.
  - `Class:Orchestrator`: A specialized agent for managing a team of other agents.
  - `Class:AgentMCPServer`: Exposes an entire agent application as a single MCP tool server.
- **Configuration:** Driven by `File:fastagent.config.yaml` for settings and secrets.

### `Component:fastmcp`
The standard Python framework for building production-grade **MCP (Model Context Protocol)** servers and clients. It handles the low-level protocol details, allowing developers to focus on implementing tools and resources. It is the designated framework for creating all new MCP services in the project.

- **Key Features:**
  - **Declarative Tool Creation:** Simple decorators (`@mcp.tool`, `@mcp.resource`) to expose Python functions.
  - **OpenAPI Generation:** Automatically creates MCP servers from existing OpenAPI specifications or FastAPI applications.
  - **In-Memory Client:** Provides a high-performance, in-memory transport for efficient testing, eliminating network overhead.
  - **Authentication:** Built-in support for securing servers and authenticating clients.

### `Component:cognee`
A cognitive architecture that provides memory for AI agents, replacing traditional RAG with an **ECL (Extract, Cognify, Load)** pipeline. It builds a structured **knowledge graph** from various data sources (text, code, etc.) to provide long-term memory and context to agents.

- **Architecture:**
  - It is deployed as a microservice, `Service:cognee-mcp`.
  - Uses `Technology:PostgreSQL` and `Technology:Neo4j` for storing graph and vector data.
  - The core logic involves a "cognify" process that extracts entities and relationships to build the knowledge graph.
- **MCP Interface (`cognee-mcp`):**
  - Exposes its functionality (e.g., `cognify`, `search`, `codify`) as MCP tools.
  - Allows the `Service:Orchestrator` and other agents to query the knowledge graph for contextual information.

### `Component:codemcp`
An MCP server that acts as a **pair programming assistant**. It provides LLMs with the tools to perform file system operations (`ReadFile`, `WriteFile`, `EditFile`) and run pre-approved, sandboxed shell commands (e.g., formatters, tests) on a local codebase. It is designed to be IDE-agnostic and ensures safety by versioning all changes with Git.

- **Configuration:** Configured via a `codemcp.toml` file, which specifies project-specific prompts and a safe list of commands the agent is allowed to execute.
- **Role in Architecture:** Acts as the "executor" or "hands" for the `Service:Orchestrator`, which delegates code modification and execution tasks to it.

### `Component:genai-toolbox`
An MCP server written in Go that provides a secure and efficient gateway to multiple **databases**. It allows agents to query and interact with structured data sources like PostgreSQL, MySQL, BigQuery, and more, without needing to manage connections or credentials directly.

- **Configuration:** Configured via a `tools.yaml` file, which defines `sources` (database connections) and `tools` (named SQL queries or operations).
- **Role in Architecture:** Acts as the dedicated **database tool server**. The `Service:Orchestrator` delegates any tasks requiring structured data access to it.

### `Component:veo-app`
This component, originating from the `vertex-ai-creative-studio`, is a web application for generative media. It provides the core logic and interface for creating images, video, and audio using Google's Vertex AI models (Imagen, Veo, Chirp). It is exposed to the rest of the system via the `Service:mcp-genmedia`.

### `Protocol:A2A` (Agent2Agent)
An open protocol for enabling communication and interoperability between different AI agents, even if they are built with different frameworks or run on different servers. It uses JSON-RPC 2.0 over HTTP(S) and allows agents to discover each other's capabilities and collaborate on tasks.

- **Role in Architecture:** The `Service:a2a-mcp-server` will act as a **bridge**, translating between the internal `Protocol:MCP` and the external `Protocol:A2A`. This allows the `Service:Orchestrator` to delegate tasks to specialized third-party agents.

---

## Relations

| Subject | Relation | Object |
|---|---|---|
| `Service:Orchestrator` | `IMPLEMENTS` | `Component:fast-agent` |
| `Service:Orchestrator` | `COMMUNICATES_WITH` | `Service:LibreChat` |
| `Service:Orchestrator` | `COMMUNICATES_WITH` | `Service:genai-toolbox` |
| `Service:Orchestrator` | `COMMUNICATES_WITH` | `Service:cognee-mcp`|
| `Service:Orchestrator` | `COMMUNICATES_WITH` | `Service:mcp-genmedia` |
| `Service:Orchestrator` | `COMMUNICATES_WITH` | `Service:codemcp` |
| `Service:Orchestrator` | `COMMUNICATES_WITH` | `Service:a2a-mcp-server` |
| `Service:a2a-mcp-server` | `IMPLEMENTS` | `Protocol:A2A` |
| `Service:a2a-mcp-server` | `USES` | `Protocol:MCP` |
| `Service:codemcp` | `IMPLEMENTS` | `Component:codemcp` |
| `Service:codemcp` | `USES` | `Technology:Python` |
| `Service:genai-toolbox` | `IMPLEMENTS` | `Component:genai-toolbox` |
| `Service:genai-toolbox` | `USES` | `Technology:Go` |
| `Service:mcp-genmedia` | `IMPLEMENTS` | `Component:veo-app` |
| `Service:mcp-genmedia` | `USES` | `Technology:Python` |
| `Service:mcp-genmedia` | `USES` | `Technology:VertexAI` |
| `Service:cognee-mcp`| `IMPLEMENTS` | `Component:cognee` |
| `Service:cognee-mcp`| `USES` | `Technology:Python` |
| `Service:cognee-mcp`| `USES` | `Technology:PostgreSQL` |
| `Service:cognee-mcp`| `USES` | `Technology:Neo4j` |
| `Service:cognee-mcp`| `SERVED_BY` | `Component:fastmcp` |
| `Service:Orchestrator` | `USES` | `Technology:Docker` |
| `Service:Orchestrator` | `USES` | `Protocol:MCP` |
| `Component:fast-agent` | `CONTAINS` | `Class:FastAgent` |
| `Component:fast-agent` | `CONTAINS` | `Class:Orchestrator` |
| `Component:fast-agent` | `CONFIGURED_BY` | `File:fastagent.config.yaml` |
| `Component:fast-agent` | `SERVED_BY` | `Component:fastmcp` |
| `Class:FastAgent` | `USES` | `Class:MCPApp` |
| `Class:Orchestrator` | `IS_A` | `Class:Agent` |
| `Class:AgentMCPServer` | `EXPOSES` | `Class:Agent` |
