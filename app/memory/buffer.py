"""
Short-term trajectory buffer.

Holds the current episode's attempts (code, execution result, reflection)
in memory so the Actor can see its recent history within the context
window without needing to query the long-term store.
"""

from __future__ import annotations

from app.core.schemas import Attempt, Reflection


class TrajectoryBuffer:
    """In-memory buffer for a single task's iteration history."""

    def __init__(self) -> None:
        self._attempts: list[Attempt] = []

    # -- Mutators ----------------------------------------------------------

    def add_attempt(self, attempt: Attempt) -> None:
        """Append a completed attempt to the trajectory."""
        self._attempts.append(attempt)

    def clear(self) -> None:
        """Reset the buffer for a new task."""
        self._attempts.clear()

    # -- Accessors ---------------------------------------------------------

    @property
    def attempts(self) -> list[Attempt]:
        return list(self._attempts)

    @property
    def reflections(self) -> list[Reflection]:
        """Return only the reflections (skipping None for passing attempts)."""
        return [a.reflection for a in self._attempts if a.reflection is not None]

    @property
    def last_attempt(self) -> Attempt | None:
        return self._attempts[-1] if self._attempts else None

    @property
    def iteration_count(self) -> int:
        return len(self._attempts)

    def format_for_prompt(self) -> str:
        """
        Render the trajectory as a human-readable string suitable for
        injection into the Actor/Reflector prompt.
        """
        if not self._attempts:
            return "(no previous attempts)"

        parts: list[str] = []
        for attempt in self._attempts:
            header = f"-- Attempt {attempt.iteration} --"
            code_section = f"Code:\n```python\n{attempt.generated_code}\n```"
            result = attempt.execution_result
            result_section = (
                f"Result: {result.status.value} | "
                f"Tests passed: {result.tests_passed}/{result.tests_total}\n"
                f"Stdout:\n{result.stdout[:500]}\n"
                f"Stderr:\n{result.stderr[:500]}"
            )
            reflection_section = ""
            if attempt.reflection:
                reflection_section = f"\nReflection:\n{attempt.reflection.content}"
            parts.append(f"{header}\n{code_section}\n{result_section}{reflection_section}")

        return "\n\n".join(parts)
