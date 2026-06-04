import logging
from dataclasses import dataclass, field

from agent_smith_crewai.llm import OllamaConfig
from agent_smith_crewai.tools.builtins import get_tools
from agent_smith_crewai.types import AgentResult

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10


@dataclass(frozen=True)
class AgentConfig:
    name: str
    system_prompt: str
    llm: OllamaConfig = field(default_factory=OllamaConfig)
    tools: list[str] | None = None
    max_iterations: int = MAX_ITERATIONS


def run_agent(task: str, config: AgentConfig) -> AgentResult:
    try:
        from crewai import Agent, Crew, Process, Task
    except ImportError:
        raise ImportError(
            "crewai is required to use the CrewAI edition. "
            "Install with: pip install crewai"
        )

    agent = Agent(
        role=config.name,
        goal=f"Complete the following task: {task}",
        backstory=config.system_prompt,
        llm=f"ollama/{config.llm.model}",
        tools=get_tools(config.tools) if config.tools else [],
        allow_delegation=False,
        max_iter=config.max_iterations,
        verbose=False,
    )

    crewai_task = Task(
        description=task,
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[crewai_task],
        process=Process.sequential,
        verbose=False,
    )

    try:
        result = crew.kickoff()
        output = str(result) if result is not None else ""
        logger.info("[%s] finished", config.name)
        return AgentResult.ok(output=output)
    except Exception as e:
        logger.error("[%s] Crew execution failed: %s", config.name, e)
        return AgentResult.fail(str(e))
