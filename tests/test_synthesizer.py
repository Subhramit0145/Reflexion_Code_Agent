"""
Unit tests for the TaskSpec Synthesizer.
"""

from unittest.mock import patch, MagicMock
from app.agent.synthesizer import synthesize_task_spec, _clean_json_response
from app.core.schemas import TaskSpec


def _mock_llm_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


def test_clean_json_response():
    assert _clean_json_response('{"a": 1}') == '{"a": 1}'
    assert _clean_json_response('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert _clean_json_response('```\n{"a": 1}\n```') == '{"a": 1}'


@patch("app.agent.synthesizer.litellm")
def test_synthesize_task_spec_success(mock_litellm):
    mock_json = """{
        "task_id": "reverse-string",
        "description": "Reverse a given string.",
        "function_signature": "def reverse_str(s: str) -> str:",
        "test_code": "assert reverse_str('abc') == 'cba'\\nprint('1 passed')"
    }"""
    mock_litellm.completion.return_value = _mock_llm_response(mock_json)

    spec = synthesize_task_spec("Write a function to reverse a string")
    assert isinstance(spec, TaskSpec)
    assert spec.task_id == "reverse-string"
    assert "def reverse_str" in spec.function_signature
    assert "assert reverse_str('abc')" in spec.test_code
