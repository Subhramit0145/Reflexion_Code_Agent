"""
Actor -- the code-generation component of the Reflexion loop.

Given a task specification and (optionally) a history of prior
reflections, the Actor prompts an LLM to produce a candidate Python
implementation.

Design note — two-tier prompting
---------------------------------
On the FIRST attempt (no reflections available) the Actor uses a
minimal, neutral system prompt that does *not* tell the model to be
"expert" or to worry about edge-cases.  This mirrors real-world
development: a first draft is written quickly and then refined.

On RETRY attempts (reflections available) the Actor switches to a
more thorough expert prompt that emphasises learning from previous
failures.  This maximises the value of verbal reinforcement by giving
the model a clear mandate to *fix* the specific issues identified by
the Reflector.
"""

from __future__ import annotations

import litellm

from app.core.config import settings
from app.core.logger import logger
from app.core.schemas import Reflection, TaskSpec


# -- Prompt used on the FIRST attempt (no reflections yet) ---------------------
# Deliberately minimal: we do NOT say "expert", do NOT mention a test
# suite, and do NOT ask for edge-case handling.  The model writes a
# natural first draft — which may contain bugs that the Evaluator will
# catch, triggering the Reflexion self-correction loop.

_SYSTEM_PROMPT_INITIAL = (
    "You are a Python programmer.  Implement the requested function.\n"
    "\n"
    "Rules:\n"
    "1. Output ONLY the Python function implementation -- no markdown\n"
    "   fences, no explanations, no test code.\n"
    "2. Include necessary imports at the top if needed.\n"
    "3. The function signature is provided; do not change it.\n"
    "4. Write a straightforward, direct implementation."
)

# -- Prompt used on RETRY attempts (reflections available) ---------------------
# Now we *do* tell the model it is an expert and that it must study the
# prior failures.  The verbal reinforcement from the Reflector is the
# mechanism that drives improvement.

_SYSTEM_PROMPT_RETRY = (
    "You are an expert Python programmer.  Your previous implementation\n"
    "had bugs that were caught by automated tests.  You have been given\n"
    "detailed feedback about what went wrong.\n"
    "\n"
    "Rules:\n"
    "1. Output ONLY the Python function implementation -- no markdown\n"
    "   fences, no explanations, no test code.\n"
    "2. Include necessary imports at the top if needed.\n"
    "3. The function signature is provided; do not change it.\n"
    "4. Study the reflections carefully and fix ALL identified issues.\n"
    "5. Write clean, correct, robust code that handles edge cases."
)


def _build_user_prompt(
    task: TaskSpec,
    reflections: list[Reflection],
    previous_code: str | None = None,
) -> str:
    """Assemble the user prompt with optional reflection history and previous attempt."""
    parts: list[str] = []

    parts.append(f"## Task\n{task.description}")
    parts.append(f"## Function Signature\n```python\n{task.function_signature}\n```")

    if previous_code and reflections:
        parts.append(
            f"## Previous Implementation (Attempt {reflections[-1].iteration})\n"
            f"```python\n{previous_code}\n```"
        )

    if reflections:
        reflection_text = "\n".join(
            f"- Attempt {r.iteration} ({r.failure_category}): {r.content}" for r in reflections
        )
        parts.append(
            f"## Lessons from Previous Attempts\n"
            f"Study these carefully and fix the identified bugs in your implementation:\n"
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
    previous_code: str | None = None,
) -> str:
    """
    Call the LLM to produce a candidate implementation.

    Parameters
    ----------
    task : TaskSpec
        The coding problem to solve.
    reflections : list[Reflection] | None
        Prior self-critiques to inject as context.
    previous_code : str | None
        Code from the previous attempt to refine.

    Returns
    -------
    str
        Raw Python source code (no markdown fences).
    """
    reflections = reflections or []
    user_prompt = _build_user_prompt(task, reflections, previous_code)

    # Select prompt tier based on whether we have prior reflections
    system_prompt = _SYSTEM_PROMPT_RETRY if reflections else _SYSTEM_PROMPT_INITIAL

    logger.info(
        f"[bold cyan]Actor[/] generating code for [bold]{task.task_id}[/] "
        f"(reflections={len(reflections)})",
        extra={"markup": True},
    )

    response = litellm.completion(
        model=settings.model_name,
        messages=[
            {"role": "system", "content": system_prompt},
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

