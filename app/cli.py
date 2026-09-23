"""
Rich interactive CLI -- the primary human interface for the agent.

Usage
-----
    python -m app.cli                        # run built-in demo task
    python -m app.cli --task-file task.json  # run a custom task
    python -m app.cli --max-iterations 5     # override iteration budget
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from app.core.config import settings
from app.core.logger import console
from app.core.schemas import AgentRun, TaskSpec
from app.agent.orchestrator import run_reflexion_loop
from app.memory.store import ReflectionStore


# -- Built-in demo task ----------------------------------------------------
# Fibonacci is simple enough to demo quickly but has a common edge case
# (n=0) that naive implementations sometimes miss, which makes it a
# good showcase for the reflection loop.

DEMO_TASK = TaskSpec(
    task_id="demo-fibonacci",
    description=(
        "Implement a function `fibonacci(n)` that returns the n-th Fibonacci "
        "number (0-indexed).  fibonacci(0) = 0, fibonacci(1) = 1, "
        "fibonacci(10) = 55.  Must handle n = 0 correctly."
    ),
    function_signature="def fibonacci(n: int) -> int:",
    test_code=(
        "assert fibonacci(0) == 0, "
        "f\"fibonacci(0) should be 0, got {fibonacci(0)}\"\n"
        "assert fibonacci(1) == 1, "
        "f\"fibonacci(1) should be 1, got {fibonacci(1)}\"\n"
        "assert fibonacci(2) == 1, "
        "f\"fibonacci(2) should be 1, got {fibonacci(2)}\"\n"
        "assert fibonacci(5) == 5, "
        "f\"fibonacci(5) should be 5, got {fibonacci(5)}\"\n"
        "assert fibonacci(10) == 55, "
        "f\"fibonacci(10) should be 55, got {fibonacci(10)}\"\n"
        "assert fibonacci(20) == 6765, "
        "f\"fibonacci(20) should be 6765, got {fibonacci(20)}\"\n"
        "print(\"All tests passed!\")\n"
        "print(\"6 passed\")\n"
    ),
)


def _print_banner() -> None:
    """Display a styled startup banner."""
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan][LOOP] Reflexion Code Agent[/]\n"
            "[dim]Autonomous Code Debugger & Test-Driven Fixer[/]\n"
            "[dim]Powered by Verbal Reinforcement Learning[/]\n\n"
            f"[dim]Model:[/] [bold]{settings.model_name}[/]  "
            f"[dim]Max iter:[/] [bold]{settings.max_iterations}[/]  "
            f"[dim]Timeout:[/] [bold]{settings.execution_timeout_seconds}s[/]",
            border_style="cyan",
            padding=(1, 3),
        )
    )
    console.print()


def _print_results(run: AgentRun) -> None:
    """Display a formatted summary table and the final solution."""
    # -- Summary table -----------------------------------------------------
    table = Table(
        title="[STATS] Run Summary",
        show_header=True,
        header_style="bold",
        border_style="dim",
    )
    table.add_column("Metric", style="cyan", min_width=20)
    table.add_column("Value", style="white")

    table.add_row("Task", run.task.task_id)
    table.add_row(
        "Solved",
        "[bold green][PASS] Yes[/]" if run.solved else "[bold red][FAIL] No[/]",
    )
    table.add_row("Iterations Used", str(run.num_iterations))
    table.add_row("Total Duration", f"{run.total_duration_seconds:.2f}s")

    if run.final_code:
        table.add_row("Final Code Length", f"{len(run.final_code)} chars")

    # Show reflection history
    reflection_count = sum(
        1 for a in run.attempts if a.reflection is not None
    )
    table.add_row("Reflections Generated", str(reflection_count))

    console.print(table)
    console.print()

    # -- Final solution (syntax-highlighted) --------------------------------
    if run.solved and run.final_code:
        syntax = Syntax(
            run.final_code,
            "python",
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
        )
        console.print(
            Panel(
                syntax,
                title="[bold green][PASS] Final Solution[/]",
                border_style="green",
                expand=False,
                padding=(1, 2),
            )
        )

    # -- Reflection trail ---------------------------------------------------
    reflections = [a.reflection for a in run.attempts if a.reflection]
    if reflections:
        console.print()
        console.print("[bold magenta][THOUGHT] Reflection Trail:[/]")
        for ref in reflections:
            console.print(
                f"  [dim]Iter {ref.iteration}[/] "
                f"[yellow]\\[{ref.failure_category}\\][/] "
                f"{ref.content}"
            )
    console.print()


def main() -> None:
    """Entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Reflexion Code Agent -- Autonomous Code Debugger CLI"
    )
    parser.add_argument(
        "--task-file",
        type=Path,
        default=None,
        help="Path to a JSON file containing a TaskSpec",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help=f"Override max iterations (default: {settings.max_iterations})",
    )
    args = parser.parse_args()

    _print_banner()

    # -- Load task ---------------------------------------------------------
    if args.task_file:
        if not args.task_file.exists():
            console.print(f"[bold red]Error:[/] {args.task_file} not found")
            sys.exit(1)
        raw = json.loads(args.task_file.read_text(encoding="utf-8"))
        task = TaskSpec(**raw)
        console.print(f"[dim]Loaded task from {args.task_file}[/]")
    else:
        task = DEMO_TASK
        console.print("[dim]Running built-in demo task (fibonacci)[/]")

    # -- Initialise memory store -------------------------------------------
    store = ReflectionStore(settings.memory_storage_path)

    console.print(
        f"\n[bold]Task:[/]        {task.task_id}\n"
        f"[bold]Description:[/] {task.description}\n"
    )

    # -- Run the Reflexion loop --------------------------------------------
    run = run_reflexion_loop(task, store, max_iterations=args.max_iterations)

    # -- Print results -----------------------------------------------------
    console.print()
    _print_results(run)


if __name__ == "__main__":
    main()
