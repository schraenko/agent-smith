"""
Examples for Agent Smith (LangChain edition).
Requires a running Ollama instance: https://ollama.com
"""

import sys

from agent_smith import (
    ApprovalDecision, OllamaConfig, Plan, Step,
    run, run_code, run_interactive, run_sequential, run_web_search, run_parallel,
)
from agent_smith.agents.builtins import web_search_agent
from agent_smith.approval import Subtask
from agent_smith.llm import make_llm

def ask_llm(question:String):
    # Create an instance of the LLM
    config = OllamaConfig()
    llm = make_llm(config)

    # Send the question to the LLM and get a response
    response = llm.invoke(question)

    # Print out the response
    print(response)

def example_run():
    result = run("Was ist die Entfernung von Nussloch nach Bruchsal?")
    print(result.output if result.success else f"Failed: {result.error}")

def example_simple():
    result = run("What is optical interferometry?", agent="web_search")
    print(result.output if result.success else f"Failed: {result.error}")
   

def example_code():
    result = run_code(
        "Write a Python function that computes the Fourier transform of a signal "
        "and plots its frequency spectrum using numpy."
    )
    print(result.output)


def example_sequential():
    llm = OllamaConfig(model="gemma4:12b", temperature=0.3)
    steps = [
        Step(
            name="research",
            agent=web_search_agent(llm),
            task_fn=lambda _: "How does a Michelson interferometer work?",
        ),
        Step(
            name="code",
            agent=__import__("agent_smith.agents.builtins", fromlist=["code_agent"]).code_agent(llm),
            task_fn=lambda r: (
                f"Based on this research:\n{r['research'].output}\n\n"
                "Write a Python simulation of a Michelson interferometer using numpy."
            ),
        ),
    ]
    wf = run_sequential(steps)
    for name, result in wf.steps.items():
        print(f"\n{'✓' if result.success else '✗'} {name}")
        print(result.output or result.error)


def example_parallel():
    llm = OllamaConfig(model="gemma4:12b")
    steps = [
        Step("history",      web_search_agent(llm), lambda _: "History of interferometry"),
        Step("applications", web_search_agent(llm), lambda _: "Modern applications of interferometry"),
        Step("ligo",         web_search_agent(llm), lambda _: "How does LIGO detect gravitational waves?"),
    ]
    wf = run_parallel(steps, max_workers=3)
    for name, result in wf.steps.items():
        print(f"\n=== {name} ===")
        print(result.output if result.success else f"Error: {result.error}")


# ─── Human-in-the-Loop ───────────────────────────────────────────────────────

# HITL_TASK = (
#     "Recherchiere die aktuellen Fortschritte in der Quantencomputing-Forschung und fasse die wichtigsten Erkenntnisse in 3 Saetzen zusammen."
# )

HITL_TASK = ("ermittle die strecke von nußloch nach bruchsal und berechne den kraftstoffverbrauch für ein fahrzeug mit 7 liter verbrauch auf 100km")

def _print_plan(plan: Plan) -> None:
    print("\n" + "=" * 60)
    print(plan.format())
    print("=" * 60)


def example_hitl():
    print("example_hitl()\n")
    """Default: CLI-Prompt mit y/n Genehmigung."""
    def approval_callback(plan: Plan) -> ApprovalDecision:
        _print_plan(plan)
        answer = input("\nPlan genehmigen? (y/n): ").strip().lower()
        if answer == "y":
            return ApprovalDecision(approved=True, feedback="ok")
        feedback = input("Feedback (optional): ").strip() or None
        return ApprovalDecision(approved=False, feedback=feedback)

    result = run_interactive(HITL_TASK, approval_callback)
    print("\n=== Ergebnis ===")
    if result.success:
        print(result.output)
    else:
        print(f"Abgebrochen: {result.error}")


def example_hitl_auto_reject():
    """Plan wird automatisch abgelehnt — demonstriert den Error-Pfad."""
    def approval_callback(plan: Plan) -> ApprovalDecision:
        _print_plan(plan)
        print("\n[Demo] Plan wird automatisch abgelehnt.")
        return ApprovalDecision(approved=False, feedback="Demo: manueller Abbruch")

    result = run_interactive(HITL_TASK, approval_callback)
    print("\n=== Ergebnis ===")
    if result.success:
        print(result.output)
    else:
        print(f"Abgebrochen: {result.error}")


def example_hitl_edit():
    """User kann einzelne Subtasks vor der Ausführung streichen."""
    def approval_callback(plan: Plan) -> ApprovalDecision:
        _print_plan(plan)
        kept: list[Subtask] = []
        for i, subtask in enumerate(plan.subtasks, 1):
            keep = input(f"  Subtask {i} [{subtask.agent}]: ausführen? (y/n): ").strip().lower()
            if keep == "y":
                kept.append(subtask)

        if not kept:
            return ApprovalDecision(approved=False, feedback="Alle Subtasks gestrichen")

        edited = Plan(subtasks=kept, reasoning=plan.reasoning + " (editiert)")
        print(f"\nUrsprünglich: {len(plan.subtasks)} Subtasks → {len(kept)} behalten.")
        return ApprovalDecision(approved=True, feedback=str(edited.to_json()))

    result = run_interactive(HITL_TASK, approval_callback)
    print("\n=== Ergebnis ===")
    if result.success:
        print(result.output)
    else:
        print(f"Abgebrochen: {result.error}")


def example_hitl_audit():
    """Zeigt nach der Ausführung den vollstaendigen Audit-Trail."""
    def approval_callback(plan: Plan) -> ApprovalDecision:
        _print_plan(plan)
        return ApprovalDecision(approved=True, feedback="ok")

    result = run_interactive(HITL_TASK, approval_callback)
    print("\n=== Ergebnis ===")
    if result.success:
        print(result.output)
    else:
        print(f"Abgebrochen: {result.error}")

    print("\n=== Audit-Trail ===")
    print(result.audit_trail.format())


if __name__ == "__main__":
    examples = {
        "run": example_run,
        "simple": example_simple,
        "code": example_code,
        "sequential": example_sequential,
        "parallel": example_parallel,
        "hitl": example_hitl,
        "hitl-auto-reject": example_hitl_auto_reject,
        "hitl-edit": example_hitl_edit,
        "hitl-audit": example_hitl_audit,
    }

    name = sys.argv[1] if len(sys.argv) > 1 else None
    fn = examples.get(name)

    if fn is not None:
        print(f"Running: {name}\n{'─' * 40}")
        fn()
    elif name:
        print("Error: Unknown example:", name)