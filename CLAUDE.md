# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a complex agentic server that exposes FastAPI, WebSocket, and SDK interfaces for multi-agent orchestration. The system uses a modern N0-IAC (No Infrastructure as Code) architecture with event-based communication.

## Development Commands

Since this is a Python project, use these commands:

```bash
# Install dependencies
pip install -r agent/requirements.txt

# Run the server (WebSocket is the primary interface)
python -m agent.application.websocket.ws_server

# Run tests
python -m pytest tests/
```

## Architecture

### Core Components

- **Application Layer** (`agent/application/`): Contains three main interfaces:
  - `api/`: FastAPI REST endpoints  
  - `websocket/`: Real-time WebSocket server (primary interface)
  - `sdk/`: SDK for programmatic access

- **Domain Layer** (`agent/domain/`): Core business logic organized into:
  - `orchestration/`: Multi-agent coordination using LangGraph StateGraph
  - `context/`: Context assembly (state, memory, available tools/agents)
  - `streaming/`: Real-time event handling and human-in-the-loop
  - `tool/`: Tool loading, execution, and validation

- **Infrastructure Layer** (`agent/infrastructure/`):
  - `config/`: YAML-based configuration for tools, workflows, permissions
  - `observability/`: Langfuse tracing and logging
  - `security/`: Access guards, input sanitization, JWT validation

### Multi-Agent Architecture

The system uses LangGraph's StateGraph for orchestration with specialized agents:
- `input_validator`: Validates and sanitizes user input
- `task_planner`: Plans task execution and decomposition
- `tool_executor`: Executes tools and API calls
- `human_reviewer`: Handles human-in-the-loop approvals
- `result_synthesizer`: Synthesizes final responses

### Context Engineering

Context is assembled from multiple sources via `ContextManager`:
- Conversation history and user profile
- Available tools and subagents  
- Relevance scoring and ranking
- Memory stores (cache, runtime, vector)

### Event-Based Communication

WebSocket communication uses structured event types:
- `markdown`: Chat messages with markdown support
- `component`: UI components (progress, forms, interactions)
- `_workflow_finish`: Workflow completion signal

Human-in-the-loop interactions use form-based UI with async field support.

## Configuration

- **Tools**: Defined in `agent/infrastructure/config/tools.yml` with API endpoints, parameters, and response mappings
- **Workflows**: Multi-step processes in `agent/infrastructure/config/workflows.yml` 
- **Permissions**: Access control in `agent/infrastructure/config/permissions.yml`

## Key Implementation Notes

- Uses instructor for Pydantic model schemas
- PostgresCheckpointer for workflow state persistence
- Interrupt-based human approval workflows
- Event-based streaming for responsive user experience
- Tenant-based multi-tenancy support
- Mock responses recommended for initial development of IO operations (APIs, DB, PDF parsing)

## WebSocket Endpoint Pattern

```
/ws/agent/{tenant_id}/{session_id}
```

The primary interface streams real-time events during agent execution, with structured payloads for different UI components and interaction patterns.