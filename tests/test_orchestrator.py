"""
Integration test for the Reflexion orchestrator loop.

Uses monkey-patching to replace the real LLM calls with deterministic
mock responses, allowing us to verify the loop logic independently of
any API key or network access.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from app.core.schemas import TaskSpec
from app.agent.orchestrator import run_reflexion_loop
from app.memory.store import ReflectionStore


# -- Test fixtures ---------------------------------------------------------

_TASK = TaskSpec(
    task_id="test-double",
    description="Implement a function that doubles a number.",
    function_signature="def double(n: int) -> int:",
    test_code=(
        "assert double(3) == 6\n"
        "assert double(0) == 0\n"
        "assert double(-2) == -4\n"
        "print(\"3 passed\")\n"
    ),
)


def _make_store() -> ReflectionStore:
    tmp = tempfile.mkdtemp()
    return ReflectionStore(Path(tmp) / "reflections.json")


def _mock_llm_response(content: str) -> MagicMock:
    """Build a mock object that mimics litellm.completion() return value."""
    msg = MagicMock()
    msg.content = content

    choice = MagicMock()
    choice.message = msg

    usage = MagicMock()
    usage.total_tokens = 100

    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    return response


# -- Tests -----------------------------------------------------------------


class TestOrchestrator:

    @patch("app.agent.actor.litellm")
    def test_solves_on_first_try(self, mock_litellm):
        """If the Actor produces correct code on try 1, loop exits immediately."""
        mock_litellm.completion.return_value = _mock_llm_response(
            "def double(n: int) -> int:\n    return n * 2"
        )

        store = _make_store()
        run = run_reflexion_loop(_TASK, store, max_iterations=3)

        assert run.solved is True
        assert run.num_iterations == 1
        assert store.size == 0  # no reflections needed

    @patch("app.agent.reflector.litellm")
    @patch("app.agent.actor.litellm")
    def test_solves_on_second_try(self, mock_actor_llm, mock_reflector_llm):
        """First attempt fails, reflection is generated, second attempt succeeds."""
        # First call: wrong code (addition instead of multiplication)
        # Second call: correct code
        mock_actor_llm.completion.side_effect = [
            _mock_llm_response(
                "def double(n: int) -> int:\n    return n + 2"
            ),
            _mock_llm_response(
                "def double(n: int) -> int:\n    return n * 2"
            ),
        ]

        # Reflector response after first failure
        mock_reflector_llm.completion.return_value = _mock_llm_response(
            "CATEGORY: wrong_operator\n"
            "REFLECTION: Used addition (+2) instead of multiplication (*2). "
            "The function should multiply the input by 2, not add 2."
        )

        store = _make_store()
        run = run_reflexion_loop(_TASK, store, max_iterations=3)

        assert run.solved is True
        assert run.num_iterations == 2
        assert store.size == 1  # one reflection stored
        assert store.get_for_task("test-double")[0].failure_category == "wrong_operator"

    @patch("app.agent.reflector.litellm")
    @patch("app.agent.actor.litellm")
    def test_fails_after_max_iterations(self, mock_actor_llm, mock_reflector_llm):
        """If the Agent never produces correct code, it should exhaust iterations."""
        # Always return wrong code
        mock_actor_llm.completion.return_value = _mock_llm_response(
            "def double(n: int) -> int:\n    return n + 2"
        )

        # Reflector always returns something
        mock_reflector_llm.completion.return_value = _mock_llm_response(
            "CATEGORY: logic_error\n"
            "REFLECTION: Still using addition instead of multiplication."
        )

        store = _make_store()
        run = run_reflexion_loop(_TASK, store, max_iterations=2)

        assert run.solved is False
        assert run.num_iterations == 2
        assert store.size == 2  # one reflection per failed iteration

    @patch("app.agent.actor.litellm")
    def test_run_records_duration(self, mock_litellm):
        """AgentRun should track total execution time."""
        mock_litellm.completion.return_value = _mock_llm_response(
            "def double(n: int) -> int:\n    return n * 2"
        )

        store = _make_store()
        run = run_reflexion_loop(_TASK, store, max_iterations=1)

        assert run.total_duration_seconds > 0

    @patch("app.agent.actor.litellm")
    def test_final_code_is_accessible(self, mock_litellm):
        """The final generated code should be retrievable from AgentRun."""
        mock_litellm.completion.return_value = _mock_llm_response(
            "def double(n: int) -> int:\n    return n * 2"
        )

        store = _make_store()
        run = run_reflexion_loop(_TASK, store, max_iterations=1)

        assert run.final_code is not None
        assert "return n * 2" in run.final_code
