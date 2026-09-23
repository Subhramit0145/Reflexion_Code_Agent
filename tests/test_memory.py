"""
Tests for the memory subsystem: TrajectoryBuffer and ReflectionStore.

All tests are self-contained and use temporary directories so they
never pollute the real data folder.
"""

import json
import tempfile
from pathlib import Path

import pytest

from app.core.schemas import (
    Attempt,
    ExecutionResult,
    ExecutionStatus,
    Reflection,
)
from app.memory.buffer import TrajectoryBuffer
from app.memory.store import ReflectionStore


# -- Helpers ---------------------------------------------------------------


def _make_reflection(task_id: str, iteration: int, content: str = "") -> Reflection:
    return Reflection(
        task_id=task_id,
        iteration=iteration,
        content=content or f"Reflection for {task_id} iter {iteration}",
        failure_category="logic_error",
    )


def _make_attempt(iteration: int, success: bool = False) -> Attempt:
    return Attempt(
        iteration=iteration,
        generated_code=f"def f(): return {iteration}",
        execution_result=ExecutionResult(
            status=(
                ExecutionStatus.SUCCESS if success
                else ExecutionStatus.TEST_FAILURE
            ),
            tests_passed=1 if success else 0,
            tests_total=1,
        ),
        reflection=(
            None if success
            else _make_reflection("test-task", iteration)
        ),
    )


# -- TrajectoryBuffer Tests ------------------------------------------------


class TestTrajectoryBuffer:
    """Unit tests for the short-term trajectory buffer."""

    def test_empty_buffer(self):
        buf = TrajectoryBuffer()
        assert buf.iteration_count == 0
        assert buf.last_attempt is None
        assert buf.reflections == []

    def test_add_single_attempt(self):
        buf = TrajectoryBuffer()
        a = _make_attempt(1)
        buf.add_attempt(a)
        assert buf.iteration_count == 1
        assert buf.last_attempt == a

    def test_add_multiple_attempts(self):
        buf = TrajectoryBuffer()
        a1 = _make_attempt(1)
        a2 = _make_attempt(2, success=True)
        buf.add_attempt(a1)
        buf.add_attempt(a2)
        assert buf.iteration_count == 2
        assert buf.last_attempt == a2

    def test_reflections_filters_none(self):
        """Only failed attempts have reflections; passing ones are None."""
        buf = TrajectoryBuffer()
        buf.add_attempt(_make_attempt(1, success=False))
        buf.add_attempt(_make_attempt(2, success=True))
        assert len(buf.reflections) == 1
        assert buf.reflections[0].iteration == 1

    def test_clear_resets(self):
        buf = TrajectoryBuffer()
        buf.add_attempt(_make_attempt(1))
        buf.add_attempt(_make_attempt(2))
        buf.clear()
        assert buf.iteration_count == 0
        assert buf.last_attempt is None

    def test_attempts_returns_copy(self):
        """Modifying the returned list should not affect internal state."""
        buf = TrajectoryBuffer()
        buf.add_attempt(_make_attempt(1))
        external = buf.attempts
        external.clear()
        assert buf.iteration_count == 1  # internal unaffected

    def test_format_for_prompt_empty(self):
        buf = TrajectoryBuffer()
        assert "no previous attempts" in buf.format_for_prompt()

    def test_format_for_prompt_populated(self):
        buf = TrajectoryBuffer()
        buf.add_attempt(_make_attempt(1))
        text = buf.format_for_prompt()
        assert "Attempt 1" in text
        assert "def f()" in text


# -- ReflectionStore Tests -------------------------------------------------


class TestReflectionStore:
    """Unit tests for the persistent reflection store."""

    def _tmp_store(self) -> ReflectionStore:
        tmp = tempfile.mkdtemp()
        return ReflectionStore(Path(tmp) / "reflections.json")

    def test_add_and_size(self):
        store = self._tmp_store()
        assert store.size == 0
        store.add(_make_reflection("t1", 1))
        assert store.size == 1

    def test_get_for_task(self):
        store = self._tmp_store()
        store.add(_make_reflection("task-a", 1))
        store.add(_make_reflection("task-b", 1))
        store.add(_make_reflection("task-a", 2))
        assert len(store.get_for_task("task-a")) == 2
        assert len(store.get_for_task("task-b")) == 1
        assert len(store.get_for_task("task-c")) == 0

    def test_persistence_across_instances(self):
        """A new store instance loading the same file should see old data."""
        tmp = tempfile.mkdtemp()
        path = Path(tmp) / "reflections.json"

        store1 = ReflectionStore(path)
        store1.add(_make_reflection("t1", 1))
        store1.add(_make_reflection("t1", 2))

        # Create a brand-new instance pointing at the same file
        store2 = ReflectionStore(path)
        assert store2.size == 2

    def test_search_keyword_match(self):
        store = self._tmp_store()
        store.add(Reflection(
            task_id="t1", iteration=1,
            content="The function failed because of an off-by-one error in the loop boundary",
            failure_category="off_by_one",
        ))
        store.add(Reflection(
            task_id="t2", iteration=1,
            content="Missing null check caused a runtime crash on empty input",
            failure_category="null_check",
        ))
        store.add(Reflection(
            task_id="t3", iteration=1,
            content="Used addition instead of multiplication for scaling",
            failure_category="wrong_operator",
        ))

        results = store.search("off-by-one loop error")
        assert len(results) >= 1
        assert results[0].failure_category == "off_by_one"

    def test_search_top_k_limit(self):
        store = self._tmp_store()
        for i in range(10):
            store.add(Reflection(
                task_id=f"t{i}", iteration=1,
                content=f"common word reflection number {i}",
                failure_category="generic",
            ))
        results = store.search("common word", top_k=3)
        assert len(results) == 3

    def test_corrupted_file_handled_gracefully(self):
        """If the JSON file is corrupted, the store should start fresh."""
        tmp = tempfile.mkdtemp()
        path = Path(tmp) / "reflections.json"
        path.write_text("NOT VALID JSON {{{{", encoding="utf-8")

        store = ReflectionStore(path)
        assert store.size == 0  # graceful fallback
