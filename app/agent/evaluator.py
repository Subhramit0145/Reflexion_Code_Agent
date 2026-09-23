"""
Evaluator -- runs the candidate code against the test suite in the
sandbox and returns a structured result.

This is intentionally thin: the real work lives in sandbox.runner.
The Evaluator's job is to be the clean interface between the sandbox
layer and the orchestrator.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logger import logger
from app.core.schemas import ExecutionResult, TaskSpec
from app.sandbox.runner import run_code_in_sandbox


def evaluate(task: TaskSpec, generated_code: str) -> ExecutionResult:
    """
    Execute *generated_code* against *task.test_code* and return results.

    Parameters
    ----------
    task : TaskSpec
        Contains the test suite to run.
    generated_code : str
        Candidate implementation produced by the Actor.

    Returns
    -------
    ExecutionResult
        Structured execution outcome.
    """
    logger.info(
        f"[bold yellow]Evaluator[/] running tests for [bold]{task.task_id}[/]",
        extra={"markup": True},
    )

    result = run_code_in_sandbox(
        implementation_code=generated_code,
        test_code=task.test_code,
        timeout=settings.execution_timeout_seconds,
    )

    if result.is_success:
        logger.info(
            f"[bold green][PASS] ALL TESTS PASSED[/] "
            f"({result.tests_passed}/{result.tests_total})",
            extra={"markup": True},
        )
    else:
        logger.warning(
            f"[bold red][FAIL] {result.status.value.upper()}[/] "
            f"({result.tests_passed}/{result.tests_total} passed)\n"
            f"  stderr: {result.stderr[:200]}",
            extra={"markup": True},
        )

    return result
