# Project Knowledge Graph

This document outlines the core entities and their relationships within the `gopilot` project ecosystem. It serves as the foundational memory for the `cognee` cognitive architecture.

## Ontology

- **Entities:** `Service`, `Component`, `Technology`, `Protocol`
- **Relations:** `USES`, `CONTAINS`, `IMPLEMENTS`, `COMMUNICATES_WITH`

---

## Entities

### Services (High-Level Microservices)
- **ID:** `Service:Orchestrator`
  - **Description:** The central brain of the system, built with `fast-agent`. It receives user prompts, plans tasks, and delegates to worker agents and tool services.
- **ID:** `Service:LibreChat`
  - **Description:** The main user-facing frontend, providing a rich chat interface for interacting with the agent system.
- **ID:** `Service:genai-toolbox`
  - **Description:** A Go-based microservice that runs as a server, exposing a vast array of database tools (Postgres, MongoDB, etc.) over a network API.
- **ID:** `Service:cognee-service`
  - **Description:** A Python-based microservice that provides the cognitive memory layer, managing and exposing the knowledge graph.
- **ID:** `Service:mcp-genmedia`
  - **Description:** A Python microservice for generative media tasks (images, video, voice).
- **ID:** `Service:codemcp`
  - **Description:** A specialized Python microservice for code generation and assistance.

### Components (Key Modules or Frameworks)
- **ID:** `Component:fast-agent`
  - **Description:** The core Python framework used to build the Orchestrator and the worker agents.
- **ID:** `Component:veo-app`
  - **Description:** A Python application for generative video, likely related to `mcp-genmedia`.

### Technologies & Protocols
- **ID:** `Technology:Python`
  - **Description:** The primary programming language for the AI/agent-based components.
- **ID:** `Technology:Go`
  - **Description:** The programming language used for the high-performance `genai-toolbox`.
- **ID:** `Technology:Docker`
  - **Description:** The containerization technology used to encapsulate and run all microservices.
- **ID:** `Protocol:MCP`
  - **Description:** Model-Context-Protocol, the communication standard for inter-service API calls.

---

## Relations

| Subject                 | Relation            | Object                  |
|-------------------------|---------------------|-------------------------|
| `Service:Orchestrator`  | `IMPLEMENTS`        | `Component:fast-agent`  |
| `Service:Orchestrator`  | `COMMUNICATES_WITH` | `Service:LibreChat`     |
| `Service:Orchestrator`  | `COMMUNICATES_WITH` | `Service:genai-toolbox` |
| `Service:Orchestrator`  | `COMMUNICATES_WITH` | `Service:cognee-service`|
| `Service:Orchestrator`  | `COMMUNICATES_WITH` | `Service:mcp-genmedia`  |
| `Service:Orchestrator`  | `COMMUNICATES_WITH` | `Service:codemcp`       |
| `Service:genai-toolbox` | `USES`              | `Technology:Go`         |
| `Service:mcp-genmedia`  | `USES`              | `Technology:Python`     |
| `Service:codemcp`       | `USES`              | `Technology:Python`     |
| `Service:cognee-service`| `USES`              | `Technology:Python`     |
| `Service:Orchestrator`  | `USES`              | `Technology:Docker`     |
| `Service:genai-toolbox` | `USES`              | `Technology:Docker`     |
| `Service:LibreChat`     | `USES`              | `Technology:Docker`     |
| `Service:Orchestrator`  | `USES`              | `Protocol:MCP`          |
