"""
Orchestrator -- drives the complete Reflexion loop.

    for each iteration:
        1. Actor generates code (using prior reflections)
        2. Evaluator runs tests in the sandbox
        3. If tests pass -> return success
        4. Reflector analyses the failure -> stores reflection
        5. Goto 1


"""

from __future__ import annotations

import time

from app.core.config import settings
from app.core.logger import console, logger
from app.core.schemas import AgentRun, Attempt, TaskSpec
from app.agent.actor import generate_code
from app.agent.evaluator import evaluate
from app.agent.reflector import reflect
from app.memory.buffer import TrajectoryBuffer
from app.memory.store import ReflectionStore


def run_reflexion_loop(
    task: TaskSpec,
    store: ReflectionStore,
    max_iterations: int | None = None,
) -> AgentRun:
   
    max_iter = max_iterations or settings.max_iterations
    buffer = TrajectoryBuffer()
    agent_run = AgentRun(task=task)

    # Retrieve any prior reflections for this task from long-term memory
    prior_reflections = store.get_for_task(task.task_id)
    if prior_reflections:
        logger.info(
            f"[dim]Found {len(prior_reflections)} prior reflections "
            f"in episodic memory[/]",
            extra={"markup": True},
        )

    start_time = time.perf_counter()

    for iteration in range(1, max_iter + 1):
        console.rule(f"[bold cyan]Iteration {iteration}/{max_iter}[/]")

        # -- 1. Actor: generate candidate code --------------------------------
        all_reflections = prior_reflections + buffer.reflections
        prev_code = (
            buffer.last_attempt.generated_code if buffer.last_attempt else None
        )
        code = generate_code(task, all_reflections, previous_code=prev_code)

        # -- 2. Evaluator: run tests ------------------------------------------
        exec_result = evaluate(task, code)

        # -- 3. Build attempt record ------------------------------------------
        attempt = Attempt(
            iteration=iteration,
            generated_code=code,
            execution_result=exec_result,
        )

        # -- 4. Check success -------------------------------------------------
        if exec_result.is_success:
            buffer.add_attempt(attempt)
            agent_run.attempts = buffer.attempts
            agent_run.solved = True
            agent_run.total_duration_seconds = round(
                time.perf_counter() - start_time, 2
            )
            console.print(
                f"\n[bold green][SOLVED] Task {task.task_id} SOLVED "
                f"on iteration {iteration}![/]\n",
            )
            return agent_run

        # -- 5. Reflector: self-critique --------------------------------------
        reflection = reflect(task, code, exec_result, iteration)
        attempt.reflection = reflection

        # Persist to both short-term buffer and long-term store
        buffer.add_attempt(attempt)
        store.add(reflection)

        logger.info(
            f"[dim]Trajectory so far: {buffer.iteration_count} attempts, "
            f"{len(buffer.reflections)} reflections[/]",
            extra={"markup": True},
        )

    # Exhausted all iterations
    agent_run.attempts = buffer.attempts
    agent_run.solved = False
    agent_run.total_duration_seconds = round(
        time.perf_counter() - start_time, 2
    )
    console.print(
        f"\n[bold red][FAILED] Task {task.task_id} NOT SOLVED "
        f"after {max_iter} iterations.[/]\n"
    )
    return agent_run
