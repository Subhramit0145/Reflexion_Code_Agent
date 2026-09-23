"""
Benchmark evaluation harness.

Runs every problem in the benchmark set under two modes:
  1. **Baseline** -- single-shot (max_iterations=1, no reflection)
  2. **Reflexion** -- multi-iteration with self-reflection

Prints a comparison table at the end showing where Reflexion
outperformed the baseline.

Usage
-----
    python -m benchmarks.run_eval
    python -m benchmarks.run_eval --max-iterations 5
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from rich.table import Table

from app.core.config import settings
from app.core.logger import console
from app.core.schemas import AgentRun
from app.agent.orchestrator import run_reflexion_loop
from app.memory.store import ReflectionStore
from benchmarks.problems import BENCHMARK_PROBLEMS


def _fresh_store(label: str, task_id: str) -> ReflectionStore:
    """Create an isolated store for each benchmark run."""
    tmp = tempfile.mkdtemp()
    return ReflectionStore(Path(tmp) / f"{label}_{task_id}.json")


def run_benchmark(max_iterations: int = 3) -> None:
    """Execute the full benchmark suite and print results."""
    console.print()
    console.rule("[bold cyan]Reflexion Benchmark Evaluation[/]")
    console.print(f"  [bold]Model:[/]      {settings.model_name}")
    console.print(f"  [bold]Problems:[/]   {len(BENCHMARK_PROBLEMS)}")
    console.print(f"  [bold]Reflexion:[/]  up to {max_iterations} iterations")
    console.print(f"  [bold]Baseline:[/]   1 iteration (zero-shot)")
    console.print()

    baseline_results: list[AgentRun] = []
    reflexion_results: list[AgentRun] = []

    for i, problem in enumerate(BENCHMARK_PROBLEMS, 1):
        console.rule(
            f"[bold]Problem {i}/{len(BENCHMARK_PROBLEMS)}: "
            f"{problem.task_id}[/]"
        )
        console.print(f"[dim]{problem.description[:100]}...[/]\n")

        # -- Baseline (single-shot, no reflection) -------------------------
        console.print("[dim]>>> Running baseline (1 iteration)...[/]")
        baseline_store = _fresh_store("baseline", problem.task_id)
        baseline_run = run_reflexion_loop(
            problem, baseline_store, max_iterations=1
        )
        baseline_results.append(baseline_run)

        # -- Reflexion (multi-iteration with reflection) -------------------
        console.print(
            f"[dim]>>> Running Reflexion ({max_iterations} iterations)...[/]"
        )
        reflexion_store = _fresh_store("reflexion", problem.task_id)
        reflexion_run = run_reflexion_loop(
            problem, reflexion_store, max_iterations=max_iterations
        )
        reflexion_results.append(reflexion_run)
        console.print()

    # -- Summary Table -----------------------------------------------------
    console.print()
    console.rule("[bold cyan]Results Summary[/]")
    console.print()

    table = Table(
        title="Baseline (1-shot) vs. Reflexion (multi-iteration)",
        show_header=True,
        header_style="bold",
        border_style="dim",
    )
    table.add_column("Problem", style="cyan", min_width=25)
    table.add_column("Baseline", justify="center", min_width=10)
    table.add_column("Reflexion", justify="center", min_width=10)
    table.add_column("Iters Used", justify="center", min_width=10)
    table.add_column("Reflections", justify="center", min_width=12)

    baseline_solved = 0
    reflexion_solved = 0

    for b_run, r_run in zip(baseline_results, reflexion_results):
        b_icon = "\u2705" if b_run.solved else "\u274c"
        r_icon = "\u2705" if r_run.solved else "\u274c"
        if b_run.solved:
            baseline_solved += 1
        if r_run.solved:
            reflexion_solved += 1

        reflection_count = sum(
            1 for a in r_run.attempts if a.reflection is not None
        )
        table.add_row(
            b_run.task.task_id,
            b_icon,
            r_icon,
            str(r_run.num_iterations),
            str(reflection_count),
        )

    total = len(BENCHMARK_PROBLEMS)
    table.add_section()
    table.add_row(
        "[bold]Total Solved[/]",
        f"[bold]{baseline_solved}/{total}[/]",
        f"[bold]{reflexion_solved}/{total}[/]",
        "",
        "",
    )

    console.print(table)
    console.print()

    # -- Verdict -----------------------------------------------------------
    improvement = reflexion_solved - baseline_solved
    b_pct = baseline_solved / total * 100
    r_pct = reflexion_solved / total * 100

    if improvement > 0:
        console.print(
            f"[bold green]\U0001f680 Reflexion solved {improvement} more "
            f"problem(s) than baseline! "
            f"({b_pct:.0f}% -> {r_pct:.0f}%, "
            f"+{improvement/total*100:.0f}% improvement)[/]"
        )
    elif improvement == 0:
        console.print(
            f"[bold yellow]Reflexion matched baseline performance "
            f"({r_pct:.0f}%).[/]"
        )
    else:
        console.print(
            "[bold red]Baseline outperformed Reflexion (unusual).[/]"
        )
    console.print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reflexion Benchmark: Baseline vs. Reflexion comparison"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=3,
        help="Max iterations for Reflexion mode (default: 3)",
    )
    args = parser.parse_args()
    run_benchmark(max_iterations=args.max_iterations)


if __name__ == "__main__":
    main()
