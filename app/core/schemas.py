"""
Pydantic data models shared across every layer of the agent.

Using explicit schemas (rather than raw dicts) gives us:
  - Automatic validation and serialisation
  - Self-documenting data flow
  - IDE autocompletion and type-safety
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# -- Enums -----------------------------------------------------------------


class ExecutionStatus(str, Enum):
    """Possible outcomes of a sandboxed code execution."""

    SUCCESS = "success"
    RUNTIME_ERROR = "runtime_error"
    TIMEOUT = "timeout"
    SYNTAX_ERROR = "syntax_error"
    TEST_FAILURE = "test_failure"


# -- Task Specification ----------------------------------------------------


class TaskSpec(BaseModel):
    """
    Describes a coding task the agent must solve.

    Attributes
    ----------
    task_id : str
        Unique identifier (e.g. "humaneval-042").
    description : str
        Natural-language problem statement.
    function_signature : str
        The function stub the agent must implement.
    test_code : str
        Python test suite that will be executed against the candidate
        implementation.  Must be self-contained.
    """

    task_id: str
    description: str
    function_signature: str
    test_code: str


# -- Sandbox Results -------------------------------------------------------


class ExecutionResult(BaseModel):
    """Captures everything that happened during a single sandbox run."""

    status: ExecutionStatus
    stdout: str = ""
    stderr: str = ""
    return_code: int | None = None
    duration_seconds: float = 0.0
    tests_passed: int = 0
    tests_total: int = 0

    @property
    def is_success(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS


# -- Reflection ------------------------------------------------------------


class Reflection(BaseModel):
    """
    A verbal self-critique produced by the Reflector after a failed attempt.

    This is the key innovation of Reflexion: instead of updating model
    weights, the agent persists a natural-language lesson learned that
    is injected into subsequent prompts.
    """

    task_id: str
    iteration: int
    content: str = Field(
        description="Natural-language reflection on what went wrong and how to fix it"
    )
    failure_category: str = Field(
        default="unknown", description="High-level failure bucket"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# -- Attempt (one full Actor cycle) ----------------------------------------


class Attempt(BaseModel):
    """A single iteration inside the Reflexion loop."""

    iteration: int
    generated_code: str
    execution_result: ExecutionResult
    reflection: Reflection | None = None


# -- Agent Run (full trajectory) -------------------------------------------


class AgentRun(BaseModel):
    """Complete record of an agent solving (or failing) a task."""

    task: TaskSpec
    attempts: list[Attempt] = Field(default_factory=list)
    solved: bool = False
    total_tokens_used: int = 0
    total_duration_seconds: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def num_iterations(self) -> int:
        return len(self.attempts)

    @property
    def final_code(self) -> str | None:
        return self.attempts[-1].generated_code if self.attempts else None
