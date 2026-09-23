"""
Actor -- the code-generation component of the Reflexion loop.

Given a task specification and (optionally) a history of prior
reflections, the Actor prompts an LLM to produce a candidate Python
implementation.
"""

from __future__ import annotations

import litellm

from app.core.config import settings
from app.core.logger import logger
from app.core.schemas import Reflection, TaskSpec


_SYSTEM_PROMPT = (
    "You are an expert Python programmer.  Your job is to implement a\n"
    "function that passes a given test suite.\n"
    "\n"
    "Rules:\n"
    "1. Output ONLY the Python function implementation -- no markdown\n"
    "   fences, no explanations, no test code.\n"
    "2. Include necessary imports at the top if needed.\n"
    "3. The function signature is provided; do not change it.\n"
    "4. Write clean, correct, efficient code."
)


def _build_user_prompt(
    task: TaskSpec,
    reflections: list[Reflection],
) -> str:
    """Assemble the user prompt with optional reflection history."""
    parts: list[str] = []

    parts.append(f"## Task\n{task.description}")
    parts.append(f"## Function Signature\n```python\n{task.function_signature}\n```")

    if reflections:
        reflection_text = "\n".join(
            f"- Attempt {r.iteration}: {r.content}" for r in reflections
        )
        parts.append(
            f"## Lessons from Previous Attempts\n"
            f"Study these carefully and avoid repeating the same mistakes:\n"
            f"{reflection_text}"
        )

    parts.append(
        "## Instructions\n"
        "Implement the function. Output ONLY valid Python code, nothing else."
    )
    return "\n\n".join(parts)


def generate_code(
    task: TaskSpec,
    reflections: list[Reflection] | None = None,
) -> str:
    """
    Call the LLM to produce a candidate implementation.

    Parameters
    ----------
    task : TaskSpec
        The coding problem to solve.
    reflections : list[Reflection] | None
        Prior self-critiques to inject as context.

    Returns
    -------
    str
        Raw Python source code (no markdown fences).
    """
    reflections = reflections or []
    user_prompt = _build_user_prompt(task, reflections)

    logger.info(
        f"[bold cyan]Actor[/] generating code for [bold]{task.task_id}[/] "
        f"(reflections={len(reflections)})",
        extra={"markup": True},
    )

    response = litellm.completion(
        model=settings.model_name,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=settings.temperature,
        max_tokens=2048,
    )

    raw: str = response.choices[0].message.content
    tokens = response.usage.total_tokens if response.usage else 0

    # Strip accidental markdown fences the LLM may have added
    code = raw.strip()
    if code.startswith("```python"):
        code = code[len("```python"):].strip()
    if code.startswith("```"):
        code = code[3:].strip()
    if code.endswith("```"):
        code = code[:-3].strip()

    logger.info(
        f"[bold cyan]Actor[/] generated {len(code)} chars, {tokens} tokens",
        extra={"markup": True},
    )
    return code
