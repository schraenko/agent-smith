# agent-smith
An evolving agent system build on langchain/langgraph

> *"The Matrix cannot tell you who you are."*

**agent-smith** is a modular, extensible framework for building agentic workflows and autonomous agents across diverse functional domains. It provides the infrastructure, orchestration primitives, and a growing library of pre-built agents — so you can focus on what your agents *do*, not on how to wire them together. Take care. We haven't took the red pill yet! It's just the beginning.

<span style="color: red">
Keep in mind that this code is for learning, experimenting and demonstrating purpose nonly! 
Don't use it for production scenarios. Never use it for use cases where security is an issue!
</span>
---

## What is agent-smith?

agent-smith enables you to:

- **Compose complex workflows** from simple, reusable agent building blocks
- **Deploy specialized agents** for tasks like data retrieval, code execution, document processing, web search, API interaction, and more
- **Orchestrate multi-agent pipelines** where agents collaborate, delegate, and hand off work to each other
- **Integrate with any LLM backend** — bring your own model or use the defaults

Whether you need a single autonomous agent or a network of cooperating agents tackling a multi-step problem, Agent Smith gives you the scaffolding to build it.

---

## Features

- **Modular agent architecture** — every agent is self-contained and composable
- **Workflow orchestration** — define sequential, parallel, or conditional agent pipelines
- **Tool use & function calling** — agents can use tools, call APIs, and interact with external systems
- **Memory & context management** — short-term and long-term memory abstractions out of the box
- **Extensible agent library** — add your own agents or use the built-in ones
- **LLM-agnostic** — works with OpenAI, Anthropic, local models, and any OpenAI-compatible API
- **Observability** — built-in logging and tracing for every agent step

---

## Built-in Agents

| Agent | Description |
|---|---|
| `WebSearchAgent` | Searches the web and summarizes results |
| `CodeExecutionAgent` | Writes and executes code in a sandboxed environment |
| `DocumentAgent` | Reads, summarizes, and extracts information from documents |
| `APIAgent` | Calls REST APIs and processes responses |
| `DataAgent` | Queries, transforms, and analyzes structured data |
| `OrchestratorAgent` | Coordinates other agents to solve complex multi-step tasks |

---

## Dependencies
```bash
pip install -r requirements.txt
pip install --upgrade setuptools
pip install -e .
```

**You need a model that supports tool use!**
The default model used is *Mistral:latest* with ollama.
You can easily pull it with
```bash
ollama pull mistral:latest 
```

## Quickstart

```bash
pip install agent-smith
```

```python
from agent_smith import AgentSmith, WebSearchAgent, OrchestratorAgent

smith = AgentSmith()

# Register agents
smith.register(WebSearchAgent())
smith.register(OrchestratorAgent())

# Run a workflow
result = smith.run("Research the latest developments in optical interferometry and write a summary.")
print(result)
```

---

## Architecture

```
┌─────────────────────────────────────────┐
│              AgentSmith Core            │
│  ┌──────────────┐  ┌─────────────────┐  │
│  │ Orchestrator │  │  Tool Registry  │  │
│  └──────┬───────┘  └────────┬────────┘  │
│         │                   │           │
│  ┌──────▼───────────────────▼────────┐  │
│  │           Agent Runtime           │  │
│  └──────┬──────────────┬─────────────┘  │
│         │              │                │
│  ┌──────▼──────┐ ┌─────▼──────┐        │
│  │   Memory    │ │  LLM Layer │        │
│  └─────────────┘ └────────────┘        │
└─────────────────────────────────────────┘
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

## Run tests
```


---

## License

Copyright (c) 2026 [Your Name]

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.