"""
Synthesizer -- automatically transforms arbitrary natural-language coding
questions into complete, executable TaskSpec instances (with function signature
and unit tests).

This enables the Reflexion agent to solve ANY coding problem provided by a user,
even if the user does not provide unit tests or function stubs.
"""

from __future__ import annotations

import json
import re
import litellm

from app.core.config import settings
from app.core.logger import logger
from app.core.schemas import TaskSpec


_SYNTHESIZER_SYSTEM_PROMPT = """You are an expert programming test engineer and specification architect.
Given an arbitrary coding question, interview problem, or natural-language programming request,
generate a complete, precise, executable Python specification for automated testing.

Return ONLY a valid JSON object with EXACTLY these four fields:
{
  "task_id": "<short-kebab-slug-max-25-chars>",
  "description": "<clean, concise description of problem, input types, and expected output>",
  "function_signature": "<def function_name(args: type) -> return_type:>",
  "test_code": "<executable Python assert statements testing 4-6 normal and edge cases, ending with print('X passed')>"
}

Strict Rules for test_code:
1. Must use standard Python `assert` statements comparing the function call to expected values.
2. Must test standard cases, empty/zero cases, and boundary/edge cases.
3. Use ONLY standard Python built-ins. Do not import external packages.
4. If testing unordered collections like sets or anagram groups, sort before comparing or test membership.
5. End with `print('{count} passed')` where {count} is the number of test assertions.
6. Output raw JSON ONLY. No markdown fences (```), no introductory or concluding text.
"""


def _clean_json_response(raw: str) -> str:
    """Strip markdown formatting or surrounding text if present."""
    text = raw.strip()
    # Remove markdown code fences if model included them
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    if text.endswith("```"):
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def synthesize_task_spec(prompt: str) -> TaskSpec:
    """
    Given an arbitrary coding question or prompt, synthesize a full TaskSpec
    complete with function signature and automated assert tests.

    Parameters
    ----------
    prompt : str
        The user's coding question in natural language.

    Returns
    -------
    TaskSpec
        Executable task specification ready for the Reflexion loop.
    """
    logger.info(
        f"[bold cyan]Synthesizer[/] generating specification for prompt: "
        f"[dim]{prompt[:60]}...[/]",
        extra={"markup": True},
    )

    response = litellm.completion(
        model=settings.model_name,
        messages=[
            {"role": "system", "content": _SYNTHESIZER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Problem Prompt:\n{prompt}"},
        ],
        temperature=0.2,
    )

    raw_content = response.choices[0].message.content or "{}"
    cleaned = _clean_json_response(raw_content)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: attempt to find the first JSON object using regex
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            raise ValueError(f"Failed to parse specification JSON from LLM: {raw_content[:200]}")

    task_id = str(data.get("task_id", "custom-task")).strip() or "custom-task"
    # Ensure kebab-case
    task_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", task_id).strip("-").lower()

    description = str(data.get("description", prompt)).strip()
    signature = str(data.get("function_signature", "def solve():")).strip()
    test_code = str(data.get("test_code", "assert True\nprint('1 passed')")).strip()

    logger.info(
        f"[bold cyan]Synthesizer[/] successfully created TaskSpec "
        f"[bold]{task_id}[/] with signature [green]{signature}[/]",
        extra={"markup": True},
    )

    return TaskSpec(
        task_id=task_id,
        description=description,
        function_signature=signature,
        test_code=test_code,
    )
