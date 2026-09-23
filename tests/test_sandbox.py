"""
Tests for the sandboxed code runner.

Validates timeout enforcement, error classification, stdout/stderr
capture, and correct test-count parsing.  These tests do NOT require
any API key — they run pure Python in subprocesses.
"""

import pytest

from app.core.schemas import ExecutionStatus
from app.sandbox.runner import run_code_in_sandbox, _count_tests


class TestCountTests:
    """Unit tests for the test-output parser."""

    def test_pytest_style_passed(self):
        passed, total = _count_tests("collected 5 items\n5 passed in 0.3s")
        assert passed == 5
        assert total == 5

    def test_pytest_style_mixed(self):
        passed, total = _count_tests("3 passed, 2 failed in 1.2s")
        assert passed == 3
        assert total == 5

    def test_unittest_style_ok(self):
        passed, total = _count_tests("Ran 4 tests in 0.001s\nOK")
        assert passed == 4
        assert total == 4

    def test_unittest_style_failures(self):
        passed, total = _count_tests(
            "Ran 4 tests in 0.001s\nFAILED (failures=1)"
        )
        assert passed == 3
        assert total == 4

    def test_no_recognisable_output(self):
        passed, total = _count_tests("hello world")
        assert passed == 0
        assert total == 0


class TestSandboxRunner:
    """Integration tests for run_code_in_sandbox."""

    def test_successful_execution(self):
        """Code that passes all assertions should return SUCCESS."""
        code = "def add(a, b): return a + b"
        tests = (
            "assert add(1, 2) == 3\n"
            "assert add(0, 0) == 0\n"
            "print(\"2 passed\")\n"
        )
        result = run_code_in_sandbox(code, tests)
        assert result.is_success
        assert result.status == ExecutionStatus.SUCCESS
        assert result.tests_passed >= 2

    def test_assertion_failure(self):
        """Code with a bug should be caught by the test suite."""
        code = "def add(a, b): return a - b  # intentional bug"
        tests = "assert add(2, 3) == 5, \"Expected 5\""
        result = run_code_in_sandbox(code, tests)
        assert not result.is_success
        assert result.status in (
            ExecutionStatus.TEST_FAILURE,
            ExecutionStatus.RUNTIME_ERROR,
        )

    def test_syntax_error(self):
        """Syntactically invalid code should be classified correctly."""
        code = "def add(a, b)\n  return a + b"  # missing colon
        tests = "assert add(1, 2) == 3"
        result = run_code_in_sandbox(code, tests)
        assert not result.is_success
        assert result.status == ExecutionStatus.SYNTAX_ERROR

    def test_timeout_enforcement(self):
        """An infinite loop should be killed after the timeout."""
        code = "import time\ntime.sleep(30)"
        tests = ""
        result = run_code_in_sandbox(code, tests, timeout=2)
        assert result.status == ExecutionStatus.TIMEOUT
        assert result.duration_seconds >= 1.5  # should be ~2s

    def test_runtime_error(self):
        """Code that raises an unhandled exception."""
        code = "def divide(a, b): return a / b"
        tests = "divide(1, 0)"
        result = run_code_in_sandbox(code, tests)
        assert not result.is_success
        assert result.status == ExecutionStatus.RUNTIME_ERROR
        assert "ZeroDivisionError" in result.stderr

    def test_stdout_capture(self):
        """Stdout from the executed code should be captured."""
        code = "print(\"hello from sandbox\")"
        tests = ""
        result = run_code_in_sandbox(code, tests)
        assert "hello from sandbox" in result.stdout

    def test_stderr_capture(self):
        """Stderr from the executed code should be captured."""
        code = "import sys; sys.stderr.write(\"warning message\")"
        tests = ""
        result = run_code_in_sandbox(code, tests)
        assert "warning message" in result.stderr

    def test_duration_is_positive(self):
        """Execution duration should always be recorded."""
        code = "x = 1 + 1"
        tests = ""
        result = run_code_in_sandbox(code, tests)
        assert result.duration_seconds > 0

    def test_empty_code_succeeds(self):
        """Empty code with no tests should succeed (no-op)."""
        result = run_code_in_sandbox("", "")
        assert result.is_success
