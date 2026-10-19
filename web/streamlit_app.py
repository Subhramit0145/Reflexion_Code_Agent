"""
Streamlit UI for the Reflexion Code Agent.

Provides a visual, interactive interface to:
  - Configure agent settings (model, iterations, timeout)
  - Submit coding tasks (or pick from built-in examples)
  - Watch the Agent iterate in real time
  - View syntax-highlighted solutions and reflection trails
  - Browse the episodic memory store

Usage
-----
    streamlit run web/streamlit_app.py
"""

from __future__ import annotations

import json
import os
import time
import sys
from pathlib import Path

import streamlit as st

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.schemas import (
    AgentRun,
    Attempt,
    ExecutionStatus,
    Reflection,
    TaskSpec,
)
from app.agent.actor import generate_code
from app.agent.evaluator import evaluate
from app.agent.reflector import reflect
from app.memory.buffer import TrajectoryBuffer
from app.memory.store import ReflectionStore

# ── Page Config ──────────────────────────────────────────

st.set_page_config(
    page_title="Reflexion Code Agent",
    page_icon="\U0001f501",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────

st.markdown("""
<style>
    /* Main background & font */
    .stApp {
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }

    /* Header gradient */
    .header-gradient {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .header-gradient h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
    }
    .header-gradient p {
        margin: 0.3rem 0 0 0;
        opacity: 0.85;
        font-size: 1rem;
    }

    /* Status cards */
    .status-card {
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 0.8rem;
    }
    .status-success {
        background: linear-gradient(135deg, #00b09b, #96c93d);
        color: white;
    }
    .status-fail {
        background: linear-gradient(135deg, #f12711, #f5af19);
        color: white;
    }
    .status-running {
        background: linear-gradient(135deg, #4facfe, #00f2fe);
        color: white;
    }

    /* Iteration card */
    .iter-card {
        background: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
        color: #cdd6f4;
    }
    .iter-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #89b4fa;
        margin-bottom: 0.5rem;
    }
    .reflection-box {
        background: #302040;
        border-left: 4px solid #cba6f7;
        border-radius: 0 8px 8px 0;
        padding: 0.8rem 1rem;
        margin-top: 0.5rem;
        color: #cba6f7;
        font-style: italic;
    }
    .reflection-category {
        color: #f9e2af;
        font-weight: 600;
        font-style: normal;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Metric boxes */
    .metric-row {
        display: flex;
        gap: 1rem;
        margin: 1rem 0;
    }
    .metric-box {
        background: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        flex: 1;
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #89b4fa;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #6c7086;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: #181825;
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: #cdd6f4;
    }

    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ── Example Tasks ────────────────────────────────────────
# Descriptions are kept deliberately MINIMAL — no edge-case hints.
# This lets the model write a natural "first draft" that may miss
# tricky cases, which the sandbox catches and the Reflector fixes.

EXAMPLE_TASKS = {
    "Select an example...": None,

    # ── Easy ──────────────────────────────────────────────
    "Fibonacci (easy)": TaskSpec(
        task_id="demo-fibonacci",
        description="Implement a function that returns the n-th Fibonacci number.",
        function_signature="def fibonacci(n: int) -> int:",
        test_code=(
            "assert fibonacci(0) == 0, f'Expected 0, got {fibonacci(0)}'\n"
            "assert fibonacci(1) == 1, f'Expected 1, got {fibonacci(1)}'\n"
            "assert fibonacci(2) == 1\n"
            "assert fibonacci(5) == 5\n"
            "assert fibonacci(10) == 55\n"
            "assert fibonacci(20) == 6765\n"
            "print('6 passed')\n"
        ),
    ),
    "Palindrome Checker (easy)": TaskSpec(
        task_id="demo-palindrome",
        description="Implement a function that checks if a string is a palindrome.",
        function_signature="def is_palindrome(s: str) -> bool:",
        test_code=(
            "assert is_palindrome('radar') == True\n"
            "assert is_palindrome('hello') == False\n"
            "assert is_palindrome('a') == True\n"
            "assert is_palindrome('') == True\n"
            "print('4 passed')\n"
        ),
    ),

    # ── Medium ────────────────────────────────────────────
    "Two Sum (medium)": TaskSpec(
        task_id="two-sum",
        description=(
            "Given a list of integers and a target, return the indices "
            "of the two numbers that add up to the target."
        ),
        function_signature="def two_sum(nums: list[int], target: int) -> list[int]:",
        test_code=(
            "assert two_sum([2, 7, 11, 15], 9) == [0, 1]\n"
            "assert two_sum([3, 2, 4], 6) == [1, 2]\n"
            "assert two_sum([3, 3], 6) == [0, 1]\n"
            "print('3 passed')\n"
        ),
    ),
    "Flatten Nested List (medium)": TaskSpec(
        task_id="flatten-nested",
        description="Given a nested list of integers, flatten it into a single list.",
        function_signature="def flatten(lst) -> list[int]:",
        test_code=(
            "assert flatten([1, 2, 3]) == [1, 2, 3]\n"
            "assert flatten([[1, 2], [3, [4, 5]], 6]) == [1, 2, 3, 4, 5, 6]\n"
            "assert flatten([]) == []\n"
            "assert flatten([1, [2, [3, [4, [5]]]]]) == [1, 2, 3, 4, 5]\n"
            "assert flatten([[[1]], [[2]], [[3]]]) == [1, 2, 3]\n"
            "print('5 passed')\n"
        ),
    ),
    "Valid Parentheses (medium)": TaskSpec(
        task_id="valid-parens",
        description=(
            "Given a string containing just brackets, determine if the "
            "input string is valid."
        ),
        function_signature="def is_valid(s: str) -> bool:",
        test_code=(
            "assert is_valid('()') == True\n"
            "assert is_valid('()[]{}') == True\n"
            "assert is_valid('(]') == False\n"
            "assert is_valid('([)]') == False\n"
            "assert is_valid('{[]}') == True\n"
            "assert is_valid('') == True\n"
            "assert is_valid('(') == False\n"
            "assert is_valid(']') == False\n"
            "print('8 passed')\n"
        ),
    ),

    # ── Hard (Multi-Iteration Demonstrations) ──────────────
    "String Compression (hard - 2 iters)": TaskSpec(
        task_id="demo-compress",
        description=(
            "Implement a function compress(s: str) -> str that performs run-length compression. "
            "Consecutive duplicate characters should be replaced with the character and its frequency. "
            "If the compressed string would not be shorter than the original string, return the original string."
        ),
        function_signature="def compress(s: str) -> str:",
        test_code=(
            "assert compress('aabcccccaaa') == 'a2bc5a3', f'Got {compress(\"aabcccccaaa\")}'\n"
            "assert compress('abcd') == 'abcd', f'Got {compress(\"abcd\")}'\n"
            "assert compress('') == '', f'Got {compress(\"\")}'\n"
            "assert compress('a') == 'a', f'Got {compress(\"a\")}'\n"
            "assert compress('abbbbbbbbbb') == 'ab10', f'Got {compress(\"abbbbbbbbbb\")}'\n"
            "print('5 passed')\n"
        ),
    ),
    "Nested JSON Path Engine (hard - 2 iters)": TaskSpec(
        task_id="nested-key-path",
        description=(
            "Implement a function query_json(data: dict | list, path: str) that retrieves a nested value "
            "using a string path syntax with dot-notation and array indices (e.g., 'users[0].profile.email'). "
            "If an index or key does not exist, return None instead of raising an error. "
            "If a key contains special characters escaped with backticks like 'data.`special.key`', handle it properly."
        ),
        function_signature="def query_json(data: dict | list, path: str):",
        test_code=(
            "d = {'users': [{'profile': {'email': 'a@b.com'}}, {'profile': None}], 'data': {'special.key': 42}}\n"
            "assert query_json(d, 'users[0].profile.email') == 'a@b.com'\n"
            "assert query_json(d, 'users[1].profile') is None\n"
            "assert query_json(d, 'users[2].profile') is None\n"
            "assert query_json(d, 'users[0].profile.phone') is None\n"
            "assert query_json(d, 'data.`special.key`') == 42\n"
            "assert query_json(d, '') == d\n"
            "print('6 passed')\n"
        ),
    ),
    "Expression Parentheses Simplifier (hard - 3 iters)": TaskSpec(
        task_id="remove-redundant-parens",
        description=(
            "Implement a function remove_redundant_parens(expr: str) -> str. "
            "Remove all unnecessary parentheses from a valid algebraic expression with '+', '-', '*', and single-character variables. "
            "Rules: "
            "1. Parentheses surrounding the entire expression when not needed by an outer operator should be removed: '((a + b))' -> 'a + b'. "
            "2. Parentheses around operands whose operator has higher or equal precedence in an associative context should be removed: '(a * b) + c' -> 'a * b + c'. "
            "3. Parentheses needed for precedence must be kept: '(a + b) * c' stays '(a + b) * c'. "
            "4. Parentheses after a subtraction must be kept if they contain '+' or '-': 'a - (b + c)' stays 'a - (b + c)'."
        ),
        function_signature="def remove_redundant_parens(expr: str) -> str:",
        test_code=(
            "assert remove_redundant_parens('((a + b))') == 'a + b'\n"
            "assert remove_redundant_parens('(a * b) + c') == 'a * b + c'\n"
            "assert remove_redundant_parens('(a + b) * c') == '(a + b) * c'\n"
            "assert remove_redundant_parens('a - (b + c)') == 'a - (b + c)', 'Subtraction scope must preserve parens'\n"
            "assert remove_redundant_parens('a + (b + c)') == 'a + b + c'\n"
            "print('5 passed')\n"
        ),
    ),
    "Merge Intervals (hard)": TaskSpec(
        task_id="merge-intervals",
        description=(
            "Given a collection of intervals, merge all overlapping intervals."
        ),
        function_signature="def merge(intervals: list[list[int]]) -> list[list[int]]:",
        test_code=(
            "assert merge([[1,3],[2,6],[8,10],[15,18]]) == [[1,6],[8,10],[15,18]]\n"
            "assert merge([[1,4],[4,5]]) == [[1,5]]\n"
            "assert merge([[1,4],[0,4]]) == [[0,4]]\n"
            "assert merge([]) == []\n"
            "assert merge([[1,4],[2,3]]) == [[1,4]]\n"
            "assert merge([[2,3],[4,5],[6,7],[8,9],[1,10]]) == [[1,10]]\n"
            "print('6 passed')\n"
        ),
    ),
    "Spiral Matrix (hard)": TaskSpec(
        task_id="spiral-matrix",
        description=(
            "Given an m x n matrix, return all elements in spiral order."
        ),
        function_signature="def spiral_order(matrix: list[list[int]]) -> list[int]:",
        test_code=(
            "assert spiral_order([[1,2,3],[4,5,6],[7,8,9]]) == [1,2,3,6,9,8,7,4,5]\n"
            "assert spiral_order([[1,2,3,4],[5,6,7,8],[9,10,11,12]]) == [1,2,3,4,8,12,11,10,9,5,6,7]\n"
            "assert spiral_order([[1]]) == [1]\n"
            "assert spiral_order([]) == []\n"
            "assert spiral_order([[1,2],[3,4]]) == [1,2,4,3]\n"
            "assert spiral_order([[1],[2],[3]]) == [1,2,3]\n"
            "print('6 passed')\n"
        ),
    ),
    "Eval Reverse Polish Notation (hard)": TaskSpec(
        task_id="eval-rpn",
        description=(
            "Evaluate an arithmetic expression in Reverse Polish Notation. "
            "Valid operators are +, -, *, /."
        ),
        function_signature="def eval_rpn(tokens: list[str]) -> int:",
        test_code=(
            "assert eval_rpn(['2','1','+','3','*']) == 9\n"
            "assert eval_rpn(['4','13','5','/','+']) == 6\n"
            "assert eval_rpn(['10','6','9','3','+','-11','*','/','*','17','+','5','+']) == 22\n"
            "assert eval_rpn(['3','4','-']) == -1\n"
            "assert eval_rpn(['6','-132','/']) == 0\n"
            "print('5 passed')\n"
        ),
    ),
    "Longest Substring Without Repeating (hard)": TaskSpec(
        task_id="longest-substr",
        description=(
            "Given a string, find the length of the longest substring "
            "without repeating characters."
        ),
        function_signature="def length_of_longest_substring(s: str) -> int:",
        test_code=(
            "assert length_of_longest_substring('abcabcbb') == 3\n"
            "assert length_of_longest_substring('bbbbb') == 1\n"
            "assert length_of_longest_substring('pwwkew') == 3\n"
            "assert length_of_longest_substring('') == 0\n"
            "assert length_of_longest_substring(' ') == 1\n"
            "assert length_of_longest_substring('dvdf') == 3\n"
            "assert length_of_longest_substring('abba') == 2\n"
            "print('7 passed')\n"
        ),
    ),
    "Max Subarray / Kadane (hard)": TaskSpec(
        task_id="max-subarray",
        description=(
            "Given an integer array, find the contiguous subarray "
            "with the largest sum and return that sum."
        ),
        function_signature="def max_subarray(nums: list[int]) -> int:",
        test_code=(
            "assert max_subarray([-2,1,-3,4,-1,2,1,-5,4]) == 6\n"
            "assert max_subarray([1]) == 1\n"
            "assert max_subarray([5,4,-1,7,8]) == 23\n"
            "assert max_subarray([-1]) == -1\n"
            "assert max_subarray([-2, -1]) == -1\n"
            "assert max_subarray([-3, -2, -1, -4]) == -1\n"
            "print('6 passed')\n"
        ),
    ),
}

# ── Session State Init ───────────────────────────────────

if "agent_run" not in st.session_state:
    st.session_state.agent_run = None
if "is_running" not in st.session_state:
    st.session_state.is_running = False
if "live_iterations" not in st.session_state:
    st.session_state.live_iterations = []
if "custom_prompt_box" not in st.session_state:
    st.session_state.custom_prompt_box = ""
if "synth_task" not in st.session_state:
    st.session_state.synth_task = None
if "synth_prompt" not in st.session_state:
    st.session_state.synth_prompt = ""

# ── Sidebar ──────────────────────────────────────────────

with st.sidebar:
    st.markdown("## \u2699\ufe0f Configuration")
    st.divider()

    model_name = st.text_input(
        "LLM Model",
        value=os.getenv("MODEL_NAME", "gemini/gemini-3.5-flash-lite"),
        help="Any LiteLLM-compatible model string",
    )

    default_key = (
        os.getenv("GEMINI_API_KEY", "")
        if "gemini" in model_name.lower()
        else os.getenv("OPENAI_API_KEY", "")
    )
    api_key = st.text_input(
        "API Key",
        value=default_key,
        type="password",
        help="Your LLM provider API key (pre-filled from .env if available)",
    )

    st.divider()

    max_iterations = st.slider(
        "Max Iterations",
        min_value=1,
        max_value=10,
        value=3,
        help="Maximum Actor-Evaluator-Reflector loops",
    )

    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.5,
        value=0.7,
        step=0.1,
        help="LLM sampling temperature (0.7-1.0 recommended for Gemini 3)",
    )

    timeout = st.slider(
        "Execution Timeout (s)",
        min_value=2,
        max_value=30,
        value=10,
        help="Sandbox timeout per code execution",
    )

    st.divider()
    st.markdown("### 🧠 Episodic Memory Mode")
    warm_start = st.checkbox(
        "Enable Warm Start (Inject Past Memory)",
        value=False,
        help="When UNCHECKED (Cold Start - recommended for video demo), the agent starts with 0 prior reflections so you can showcase the live multi-iteration Reflexion loop! When CHECKED (Warm Start), it injects previously stored reflections to show that the agent learned.",
    )
    if st.button("🗑️ Reset Stored Reflections", use_container_width=True, help="Wipe data/reflections.json back to an empty slate"):
        from app.core.config import settings
        settings.memory_storage_path.write_text("[]", encoding="utf-8")
        st.success("Cleared reflection memory store!")
        st.rerun()

    st.divider()
    st.markdown("### \U0001f4da About")
    st.markdown(
        "This agent implements **Reflexion** "
        "([Shinn et al., NeurIPS 2023]"
        "(https://arxiv.org/abs/2303.11366)) "
        "\u2014 verbal reinforcement learning "
        "without weight updates."
    )
    st.markdown(
        "The agent generates code, runs tests, "
        "self-reflects on failures, and retries "
        "with accumulated insights."
    )

# ── Header ───────────────────────────────────────────────

st.markdown("""
<div class="header-gradient">
    <h1>\U0001f501 Reflexion Code Agent</h1>
    <p>Autonomous Code Debugger & Test-Driven Fixer \u2014 Powered by Verbal Reinforcement Learning</p>
</div>
""", unsafe_allow_html=True)

# ── Task Input ───────────────────────────────────────────

input_mode = st.radio(
    "Select Input Method:",
    options=[
        "✨ Any Coding Problem (Auto-Solve)",
        "📋 Pre-Built Benchmark Examples",
        "📝 Manual Form",
        "📄 JSON Spec",
    ],
    horizontal=True,
    help="Choose how to supply the coding task. 'Any Coding Problem' lets you paste any question in plain English.",
)

if input_mode == "✨ Any Coding Problem (Auto-Solve)":
    st.markdown(
        "**Paste or type ANY coding question.** The agent will automatically deduce the "
        "function signature, generate a full unit test suite, and run the self-correcting "
        "Reflexion loop to deliver a verified solution."
    )
    custom_prompt_val = st.text_area(
        "Your Coding Problem / Requirements",
        key="custom_prompt_box",
        height=130,
        placeholder=(
            "e.g. 'Write a function that groups anagrams together from a list of words' "
            "or 'Given a string, check if it has valid matching brackets' "
            "or paste any LeetCode / interview problem statement..."
        ),
        help="Natural language prompt for any coding question or feature.",
    )

    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        if st.button("💡 Group Anagrams", use_container_width=True):
            st.session_state.custom_prompt_box = (
                "Given an array of strings, group the anagrams together. "
                "Return the groups as a list of lists."
            )
            st.session_state.synth_task = None
            st.session_state.synth_prompt = ""
            st.session_state.agent_run = None
            st.rerun()
    with col_s2:
        if st.button("💡 Roman to Integer", use_container_width=True):
            st.session_state.custom_prompt_box = (
                "Convert a Roman numeral string (e.g. 'IX', 'LVIII', 'MCMXCIV') to an integer."
            )
            st.session_state.synth_task = None
            st.session_state.synth_prompt = ""
            st.session_state.agent_run = None
            st.rerun()
    with col_s3:
        if st.button("💡 Longest Palindrome Substring", use_container_width=True):
            st.session_state.custom_prompt_box = (
                "Given a string s, return the longest palindromic substring in s."
            )
            st.session_state.synth_task = None
            st.session_state.synth_prompt = ""
            st.session_state.agent_run = None
            st.rerun()
    with col_s4:
        if st.button("💡 Valid Parentheses String", use_container_width=True):
            st.session_state.custom_prompt_box = (
                "Given a string containing brackets '(', ')', '{', '}', '[' and ']' "
                "determine if the input string is valid."
            )
            st.session_state.synth_task = None
            st.session_state.synth_prompt = ""
            st.session_state.agent_run = None
            st.rerun()

    col_synth_btn, _ = st.columns([2, 2])
    with col_synth_btn:
        synth_clicked = st.button(
            "🪄 Synthesize & Preview Test Suite",
            help="Generate the signature and tests to inspect them before running",
        )

    if synth_clicked:
        p_text = (st.session_state.get("custom_prompt_box") or custom_prompt_val or "").strip()
        if not p_text:
            st.warning("⚠️ Please type or paste a coding question above first.")
        else:
            with st.spinner("Synthesizing function signature & unit tests..."):
                from app.agent.synthesizer import synthesize_task_spec
                st.session_state.synth_task = synthesize_task_spec(p_text)
                st.session_state.synth_prompt = p_text
                st.session_state.agent_run = None
                st.success(f"✅ Synthesized Task: **{st.session_state.synth_task.task_id}**")

    if st.session_state.synth_task:
        st.markdown(
            f"**Task ID:** `{st.session_state.synth_task.task_id}` &nbsp;|&nbsp; "
            f"**Signature:** `{st.session_state.synth_task.function_signature}`"
        )
        with st.expander("🧪 View Generated Test Suite", expanded=True):
            st.code(st.session_state.synth_task.test_code, language="python")

elif input_mode == "📋 Pre-Built Benchmark Examples":
    selected_example = st.selectbox(
        "Choose an example benchmark problem:",
        options=[k for k in EXAMPLE_TASKS.keys() if k != "Select an example..."],
    )
    example_task = EXAMPLE_TASKS.get(selected_example)
    if example_task:
        st.markdown(f"**Task ID:** `{example_task.task_id}` &nbsp;|&nbsp; **Signature:** `{example_task.function_signature}`")
        st.markdown(f"**Description:** {example_task.description}")
        with st.expander("📋 View Benchmark Tests", expanded=False):
            st.code(example_task.test_code, language="python")

elif input_mode == "📝 Manual Form":
    col1, col2 = st.columns(2)
    with col1:
        task_id = st.text_input("Task ID", value="my-task", help="A unique identifier for this task")
        description = st.text_area("Problem Description", value="", height=120, help="Natural-language description of the problem")
    with col2:
        function_signature = st.text_input("Function Signature", value="def solve():", help="The function stub")
        test_code = st.text_area("Test Code (Python)", value="", height=120, help="Assert-based tests")

    if st.button("🪄 Auto-Generate Signature & Tests from Description"):
        if not description.strip():
            st.warning("Please enter a Problem Description first.")
        else:
            with st.spinner("Generating signature & tests..."):
                from app.agent.synthesizer import synthesize_task_spec
                generated_spec = synthesize_task_spec(description.strip())
                st.session_state.synth_task = generated_spec
                st.success(f"Generated signature: `{generated_spec.function_signature}`")
                st.code(generated_spec.test_code, language="python")

elif input_mode == "📄 JSON Spec":
    json_input = st.text_area(
        "Paste a TaskSpec JSON",
        height=200,
        placeholder='{"task_id": "...", "description": "...", "function_signature": "...", "test_code": "..."}',
    )

st.divider()

# ── Run / Clear Buttons ──────────────────────────────────

run_col1, run_col2 = st.columns([3, 1])
with run_col1:
    run_clicked = st.button(
        "\U0001f680  Run Reflexion Agent",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.is_running,
    )
with run_col2:
    if st.button("🧹 Clear Results", use_container_width=True, disabled=st.session_state.is_running):
        st.session_state.agent_run = None
        st.session_state.live_iterations = []
        st.session_state.synth_task = None
        st.session_state.synth_prompt = ""
        st.rerun()

# ── Agent Execution ──────────────────────────────────────

if run_clicked:
    # Validate API key
    if not api_key:
        st.error("\u274c Please enter your API key in the sidebar.")
        st.stop()

    # Configure the LLM settings early
    import os
    os.environ["MODEL_NAME"] = model_name
    os.environ["TEMPERATURE"] = str(temperature)
    os.environ["MAX_ITERATIONS"] = str(max_iterations)
    os.environ["EXECUTION_TIMEOUT_SECONDS"] = str(timeout)

    # Set API key based on model if provided
    if api_key.strip():
        if "gemini" in model_name.lower():
            os.environ["GEMINI_API_KEY"] = api_key.strip()
        elif "claude" in model_name.lower() or "anthropic" in model_name.lower():
            os.environ["ANTHROPIC_API_KEY"] = api_key.strip()
        else:
            os.environ["OPENAI_API_KEY"] = api_key.strip()

    # Reload settings
    from app.core.config import Settings
    import app.core.config
    settings = Settings()
    app.core.config.settings = settings
    settings.inject_api_keys()

    # Determine task strictly based on active input_mode
    try:
        if input_mode == "✨ Any Coding Problem (Auto-Solve)":
            prompt_text = (st.session_state.get("custom_prompt_box") or custom_prompt_val or "").strip()
            if not prompt_text:
                st.error("❌ Please enter a coding question or problem description above.")
                st.stop()
            if st.session_state.get("synth_task") and st.session_state.get("synth_prompt") == prompt_text:
                task = st.session_state.synth_task
            else:
                with st.spinner("✨ Synthesizing signature & test suite from your question..."):
                    from app.agent.synthesizer import synthesize_task_spec
                    task = synthesize_task_spec(prompt_text)
                    st.session_state.synth_task = task
                    st.session_state.synth_prompt = prompt_text
            st.info(f"🎯 **Target Function:** `{task.function_signature}` (Task ID: `{task.task_id}`)")
            with st.expander("🧪 Synthesized Unit Tests", expanded=False):
                st.code(task.test_code, language="python")

        elif input_mode == "📋 Pre-Built Benchmark Examples":
            task = EXAMPLE_TASKS[selected_example]

        elif input_mode == "📝 Manual Form":
            if not description.strip() or not function_signature.strip() or not test_code.strip():
                st.error("❌ Please fill in Problem Description, Function Signature, and Test Code.")
                st.stop()
            task = TaskSpec(
                task_id=task_id.strip() or "custom-task",
                description=description.strip(),
                function_signature=function_signature.strip(),
                test_code=test_code.strip(),
            )

        elif input_mode == "📄 JSON Spec":
            if not json_input.strip():
                st.error("❌ Please paste a valid TaskSpec JSON.")
                st.stop()
            raw = json.loads(json_input)
            task = TaskSpec(**raw)

    except Exception as e:
        st.error(f"❌ Invalid task: {e}")
        st.stop()

    # Run the agent with live UI updates
    st.session_state.is_running = True
    st.session_state.agent_run = None
    st.session_state.live_iterations = []

    store = ReflectionStore(settings.memory_storage_path)
    buffer = TrajectoryBuffer()
    prior_reflections = store.get_for_task(task.task_id) if warm_start else []
    if warm_start and prior_reflections:
        st.info(f"🧠 Warm Start Active: Injected {len(prior_reflections)} prior reflection(s) from memory.")
    elif not warm_start:
        st.caption("❄️ Cold Start Active: Starting fresh with 0 prior reflections.")

    results_container = st.container()
    progress_bar = st.progress(0, text="Starting agent...")
    status_placeholder = st.empty()
    iterations_container = st.container()

    agent_run = AgentRun(task=task)
    solved = False
    start_time = time.perf_counter()

    for iteration in range(1, max_iterations + 1):
        progress = iteration / max_iterations
        progress_bar.progress(progress, text=f"Iteration {iteration}/{max_iterations}")

        with iterations_container:
            st.markdown(f"""
            <div class="iter-card">
                <div class="iter-header">\U0001f504 Iteration {iteration} of {max_iterations}</div>
            </div>
            """, unsafe_allow_html=True)

            # -- Actor -------------------------------------------------
            with st.spinner(f"\U0001f3ad Actor generating code (iteration {iteration})..."):
                all_reflections = prior_reflections + buffer.reflections
                prev_code = (
                    buffer.last_attempt.generated_code if buffer.last_attempt else None
                )
                try:
                    code = generate_code(task, all_reflections, previous_code=prev_code)
                except Exception as e:
                    st.error(f"\u274c Actor failed: {e}")
                    break

            st.markdown("**\U0001f3ad Generated Code:**")
            st.code(code, language="python")

            # -- Evaluator ---------------------------------------------
            with st.spinner("\U0001f9ea Evaluator running tests in sandbox..."):
                exec_result = evaluate(task, code)

            # Show result
            if exec_result.is_success:
                st.markdown(f"""
                <div class="status-card status-success">
                    <strong>\u2705 ALL TESTS PASSED</strong> ({exec_result.tests_passed}/{exec_result.tests_total})
                    &nbsp;|&nbsp; Duration: {exec_result.duration_seconds:.3f}s
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="status-card status-fail">
                    <strong>\u274c {exec_result.status.value.upper()}</strong>
                    ({exec_result.tests_passed}/{exec_result.tests_total} passed)
                    &nbsp;|&nbsp; Duration: {exec_result.duration_seconds:.3f}s
                </div>
                """, unsafe_allow_html=True)
                if exec_result.stderr:
                    with st.expander("\U0001f4cb Execution Output", expanded=False):
                        if exec_result.stdout:
                            st.text(f"stdout:\n{exec_result.stdout[:500]}")
                        st.text(f"stderr:\n{exec_result.stderr[:500]}")

            # Build attempt
            attempt = Attempt(
                iteration=iteration,
                generated_code=code,
                execution_result=exec_result,
            )

            # -- Success? ----------------------------------------------
            if exec_result.is_success:
                buffer.add_attempt(attempt)
                solved = True
                break

            # -- Reflector ---------------------------------------------
            with st.spinner("\U0001f4ad Reflector analysing failure..."):
                try:
                    reflection = reflect(task, code, exec_result, iteration)
                except Exception as e:
                    st.error(f"\u274c Reflector failed: {e}")
                    attempt.reflection = None
                    buffer.add_attempt(attempt)
                    break

            attempt.reflection = reflection
            buffer.add_attempt(attempt)
            store.add(reflection)

            st.markdown(f"""
            <div class="reflection-box">
                <div class="reflection-category">\U0001f3f7\ufe0f {reflection.failure_category}</div>
                \U0001f4ad {reflection.content}
            </div>
            """, unsafe_allow_html=True)

        st.divider()

    total_duration = round(time.perf_counter() - start_time, 2)

    # Build final AgentRun
    agent_run.attempts = buffer.attempts
    agent_run.solved = solved
    agent_run.total_duration_seconds = total_duration
    st.session_state.agent_run = agent_run
    st.session_state.is_running = False
    progress_bar.empty()

    # ── Final Results ────────────────────────────────────
    st.divider()

    if solved:
        st.markdown("""
        <div class="status-card status-success">
            <h3 style="margin:0">\U0001f389 Task Solved!</h3>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="status-card status-fail">
            <h3 style="margin:0">\u274c Task Not Solved</h3>
            <p style="margin:0.3rem 0 0 0">Maximum iterations exhausted.</p>
        </div>
        """, unsafe_allow_html=True)

    # Metrics
    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-box">
            <div class="metric-value">{agent_run.num_iterations}</div>
            <div class="metric-label">Iterations</div>
        </div>
        <div class="metric-box">
            <div class="metric-value">{total_duration:.1f}s</div>
            <div class="metric-label">Total Time</div>
        </div>
        <div class="metric-box">
            <div class="metric-value">{sum(1 for a in agent_run.attempts if a.reflection)}</div>
            <div class="metric-label">Reflections</div>
        </div>
        <div class="metric-box">
            <div class="metric-value">{"\u2705" if solved else "\u274c"}</div>
            <div class="metric-label">Result</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Final solution
    if solved and agent_run.final_code:
        st.markdown("### \u2705 Final Verified Solution")
        st.code(agent_run.final_code, language="python")

    # Reflection trail
    reflections = [a.reflection for a in agent_run.attempts if a.reflection]
    if reflections:
        st.markdown("### \U0001f4ad Reflection Trail")
        for ref in reflections:
            st.markdown(f"""
            <div class="reflection-box">
                <div class="reflection-category">
                    Iteration {ref.iteration} \u2014 {ref.failure_category}
                </div>
                {ref.content}
            </div>
            """, unsafe_allow_html=True)

# ── Previous Run Display ─────────────────────────────────

elif st.session_state.agent_run and not st.session_state.is_running:
    run = st.session_state.agent_run
    st.info(
        f"\U0001f4ca Showing results from previous run: "
        f"**{run.task.task_id}** \u2014 "
        f"{'\u2705 Solved' if run.solved else '\u274c Not Solved'} "
        f"in {run.num_iterations} iteration(s)"
    )

    if run.solved and run.final_code:
        st.markdown("### \u2705 Final Solution")
        st.code(run.final_code, language="python")

    reflections = [a.reflection for a in run.attempts if a.reflection]
    if reflections:
        st.markdown("### \U0001f4ad Reflection Trail")
        for ref in reflections:
            st.markdown(f"""
            <div class="reflection-box">
                <div class="reflection-category">
                    Iteration {ref.iteration} \u2014 {ref.failure_category}
                </div>
                {ref.content}
            </div>
            """, unsafe_allow_html=True)

# ── Footer ───────────────────────────────────────────────

st.divider()
st.markdown(
    "<div style=\'text-align:center; color:#6c7086; font-size:0.85rem\'>"
    "Built with Reflexion (Shinn et al., NeurIPS 2023) \u2022 "
    "Powered by LiteLLM + Streamlit"
    "</div>",
    unsafe_allow_html=True,
)
