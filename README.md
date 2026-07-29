# agent-smith

A modular agent framework built on LangChain for Ollama-based LLMs.

> *"The Matrix cannot tell you who you are."*

**agent-smith** is a modular, extensible framework for building agentic workflows and autonomous agents across diverse functional domains. It provides the infrastructure, orchestration primitives, and a growing library of pre-built agents — so you can focus on what your agents *do*, not on how to wire them together. Take care. We haven't took the red pill yet! It's just the beginning.

> **Note:** This code is for learning, experimenting and demonstrating purposes only!
> Don't use it for production scenarios. Never use it for use cases where security is an issue!

---

## What is agent-smith?

agent-smith enables you to:

- **Compose complex workflows** from simple, reusable agent building blocks
- **Deploy specialized agents** for tasks like data retrieval, code execution, document processing, web search, API interaction, and more
- **Orchestrate multi-agent pipelines** where agents collaborate, delegate, and hand off work to each other
- **Track every step** with built-in audit trails for full observability

Whether you need a single autonomous agent or a network of cooperating agents tackling a multi-step problem, Agent Smith gives you the scaffolding to build it.

---

## Features

- **Modular agent architecture** — every agent is self-contained and composable
- **Workflow orchestration** — define sequential, parallel, or conditional agent pipelines
- **Tool use & function calling** — agents can use tools, call APIs, and interact with external systems
- **Audit trail** — full observability of every LLM call, tool invocation, and delegation
- **Extensible agent library** — add your own agents or use the built-in ones
- **Ollama-only** — works with any Ollama-compatible model (default: gemma4:12b)
- **MCP Server support** — mock data servers for testing and prototyping

---

## Built-in Agents

| Agent | Description |
|---|---|
| `WebSearchAgent` | Searches the web and summarizes results |
| `CodeExecutionAgent` | Writes and executes code in a sandboxed environment |
| `DocumentAgent` | Reads, summarizes, and extracts information from documents |
| `APIAgent` | Calls REST APIs and processes responses |
| `DataAgent` | Queries, transforms, and analyzes structured data |
| `OrchestratorAgent` | Coordinates other agents via delegation to solve complex multi-step tasks |

---

## Quickstart

### Installation

```bash
pip install -r requirements.txt
pip install -e .
```

### Basic Usage

```python
from agent_smith import run

# Simple task with a specific agent
result = run("What is the capital of France?", agent="web_search")
print(result.output)

# Complex task with orchestrator
result = run("Research and summarize: What is agent-smith?")
print(result.output)

# View the full audit trail
print(result.audit_trail.format())
```

### Ollama Setup

You need a running Ollama instance with a model that supports tool use.
The default model is `gemma4:12b`.

```bash
# Pull the default model
ollama pull gemma4:12b

# Or use any other tool-capable model
ollama pull mistral:latest
```

---

## MCP Server

agent-smith includes a mock MCP server for testing:

```bash
# Start the rain sensor mock server
python mcp_servers/rain_sensor/server.py
# Server runs on http://localhost:8080/sse
```

### Available Tools

| Tool | Description |
|------|-------------|
| `get_all_sensors()` | All 6 sensors with random data |
| `get_sensor(sensor_id)` | Single sensor by ID |
| `get_rain_level()` | Average/min/max across all sensors |
| `get_alerts(threshold)` | Sensors above threshold |

---

## Dependencies

```
langchain>=1.0.0
langchain-ollama>=0.3.0
langchain-core>=0.3.0
httpx>=0.27.0
pandas>=2.0.0
ddgs>=7.0.0
mcp[cli]>=1.27
```

---

## Tests

```bash
# Unit tests (mocked, no Ollama needed)
python -m pytest tests/

# Integration tests (needs Ollama + gemma4:12b)
python -m pytest tests/test_ollama_integration.py -v -s

# With coverage
python -m pytest --cov=agent_smith
```

---

## Contributing

Contributions are welcome! If you want to add a new agent, improve the orchestration engine, or fix a bug:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-new-agent`)
3. Commit your changes
4. Open a pull request

Please make sure your code is well-documented and includes tests.

---

## License

Copyright (c) 2026

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
