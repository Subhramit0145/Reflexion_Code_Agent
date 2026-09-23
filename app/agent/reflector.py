"""
Self-Reflector -- the introspective core of Reflexion.

After the Evaluator reports a failure, the Reflector analyses the
failed trajectory (code + execution output) and produces a
*verbal reflection*: a concise, actionable natural-language critique
explaining what went wrong and what to do differently next time.

This reflection is then stored in episodic memory and injected into
the Actor's next prompt -- closing the self-improvement loop without
any gradient updates.
"""

from __future__ import annotations

import litellm

from app.core.config import settings
from app.core.logger import logger
from app.core.schemas import ExecutionResult, Reflection, TaskSpec


_SYSTEM_PROMPT = (
    "You are a senior code reviewer performing post-mortem analysis.\n"
    "\n"
    "Given:\n"
    "  - A task description and function signature\n"
    "  - The candidate code that was generated\n"
    "  - The execution result (stdout, stderr, status)\n"
    "\n"
    "Your job:\n"
    "1. Identify the ROOT CAUSE of the failure (not just symptoms).\n"
    "2. Classify the failure (e.g., off-by-one, missing edge case, wrong\n"
    "   algorithm, misunderstood requirements, syntax error).\n"
    "3. Write a SHORT, ACTIONABLE reflection (2-4 sentences) that a\n"
    "   programmer could use to fix the code on the next attempt.\n"
    "\n"
    "Output format (plain text, no markdown):\n"
    "CATEGORY: <failure_category>\n"
    "REFLECTION: <your reflection>"
)


def _build_reflection_prompt(
    task: TaskSpec,
    code: str,
    result: ExecutionResult,
    iteration: int,
) -> str:
    return (
        f"## Task\n{task.description}\n\n"
        f"## Function Signature\n{task.function_signature}\n\n"
        f"## Candidate Code (Attempt {iteration})\n"
        f"```python\n{code}\n```\n\n"
        f"## Execution Result\n"
        f"Status: {result.status.value}\n"
        f"Tests passed: {result.tests_passed}/{result.tests_total}\n"
        f"Stdout:\n{result.stdout[:600]}\n"
        f"Stderr:\n{result.stderr[:600]}\n"
    )


def _parse_reflection(raw: str, task_id: str, iteration: int) -> Reflection:
    """Parse the LLM output into a structured Reflection."""
    category = "unknown"
    content = raw.strip()

    for line in raw.strip().splitlines():
        upper_line = line.upper()
        if upper_line.startswith("CATEGORY:"):
            category = line.split(":", 1)[1].strip().lower()
        elif upper_line.startswith("REFLECTION:"):
            content = line.split(":", 1)[1].strip()

    return Reflection(
        task_id=task_id,
        iteration=iteration,
        content=content,
        failure_category=category,
    )


def reflect(
    task: TaskSpec,
    code: str,
    result: ExecutionResult,
    iteration: int,
) -> Reflection:
    """
    Generate a verbal self-reflection for a failed attempt.

    Parameters
    ----------
    task : TaskSpec
        The problem being solved.
    code : str
        The candidate code that failed.
    result : ExecutionResult
        Execution output and status.
    iteration : int
        Current iteration number (1-indexed).

    Returns
    -------
    Reflection
        Structured verbal critique with failure category.
    """
    logger.info(
        f"[bold magenta]Reflector[/] analysing failure for [bold]{task.task_id}[/] "
        f"(iteration {iteration})",
        extra={"markup": True},
    )

    user_prompt = _build_reflection_prompt(task, code, result, iteration)

    response = litellm.completion(
        model=settings.model_name,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=512,
    )

    raw: str = response.choices[0].message.content
    reflection = _parse_reflection(raw, task.task_id, iteration)

    logger.info(
        f"[bold magenta]Reflector[/] [{reflection.failure_category}] "
        f"{reflection.content}",
        extra={"markup": True},
    )

    return reflection
