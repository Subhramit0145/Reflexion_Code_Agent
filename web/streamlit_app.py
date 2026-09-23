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

EXAMPLE_TASKS = {
    "Select an example...": None,
    "Fibonacci (easy)": TaskSpec(
        task_id="demo-fibonacci",
        description=(
            "Implement a function fibonacci(n) that returns the n-th Fibonacci "
            "number (0-indexed). fibonacci(0) = 0, fibonacci(1) = 1, "
            "fibonacci(10) = 55. Must handle n = 0 correctly."
        ),
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
    "Two Sum (medium)": TaskSpec(
        task_id="two-sum",
        description=(
            "Given a list of integers nums and an integer target, return "
            "the indices of the two numbers that add up to target. "
            "Return indices in ascending order. Each input has exactly one solution."
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
        description=(
            "Given a nested list of integers, flatten it into a single list. "
            "Handle arbitrary nesting depth. "
            "Example: [[1,2],[3,[4,5]],6] -> [1,2,3,4,5,6]"
        ),
        function_signature="def flatten(lst) -> list[int]:",
        test_code=(
            "assert flatten([1, 2, 3]) == [1, 2, 3]\n"
            "assert flatten([[1, 2], [3, [4, 5]], 6]) == [1, 2, 3, 4, 5, 6]\n"
            "assert flatten([]) == []\n"
            "assert flatten([1, [2, [3, [4, [5]]]]]) == [1, 2, 3, 4, 5]\n"
            "print('4 passed')\n"
        ),
    ),
    "Valid Parentheses (medium)": TaskSpec(
        task_id="valid-parens",
        description=(
            "Given a string s containing just '(', ')', '{', '}', '[' and ']', "
            "determine if the input string is valid. Open brackets must be "
            "closed by the same type in the correct order. Empty string is valid."
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
            "print('7 passed')\n"
        ),
    ),
    "Max Subarray / Kadane (hard)": TaskSpec(
        task_id="max-subarray",
        description=(
            "Given an integer array nums, find the contiguous subarray "
            "with the largest sum and return that sum. The array contains "
            "at least one number. Must handle all-negative arrays correctly."
        ),
        function_signature="def max_subarray(nums: list[int]) -> int:",
        test_code=(
            "assert max_subarray([-2,1,-3,4,-1,2,1,-5,4]) == 6\n"
            "assert max_subarray([1]) == 1\n"
            "assert max_subarray([5,4,-1,7,8]) == 23\n"
            "assert max_subarray([-1]) == -1\n"
            "assert max_subarray([-2, -1]) == -1\n"
            "print('5 passed')\n"
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

# ── Sidebar ──────────────────────────────────────────────

with st.sidebar:
    st.markdown("## \u2699\ufe0f Configuration")
    st.divider()

    model_name = st.text_input(
        "LLM Model",
        value="gemini/gemini-3.6-flash",
        help="Any LiteLLM-compatible model string",
    )

    api_key = st.text_input(
        "API Key",
        type="password",
        help="Your LLM provider API key",
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
        value=0.2,
        step=0.1,
        help="LLM sampling temperature (lower = more deterministic)",
    )

    timeout = st.slider(
        "Execution Timeout (s)",
        min_value=2,
        max_value=30,
        value=10,
        help="Sandbox timeout per code execution",
    )

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

col_example, col_spacer = st.columns([3, 1])
with col_example:
    selected_example = st.selectbox(
        "\U0001f4cb Load an example task",
        options=list(EXAMPLE_TASKS.keys()),
    )

# Pre-fill from example if selected
example_task = EXAMPLE_TASKS.get(selected_example)

tab_input, tab_json = st.tabs(["\U0001f4dd Form Input", "\U0001f4c4 JSON Input"])

with tab_input:
    col1, col2 = st.columns(2)
    with col1:
        task_id = st.text_input(
            "Task ID",
            value=example_task.task_id if example_task else "my-task",
            help="A unique identifier for this task",
        )
        description = st.text_area(
            "Problem Description",
            value=example_task.description if example_task else "",
            height=120,
            help="Natural-language description of the coding problem",
        )
    with col2:
        function_signature = st.text_input(
            "Function Signature",
            value=example_task.function_signature if example_task else "def solve():",
            help="The function stub the agent must implement",
        )
        test_code = st.text_area(
            "Test Code (Python)",
            value=example_task.test_code if example_task else "",
            height=120,
            help="Assert-based tests to verify the implementation",
        )

with tab_json:
    json_input = st.text_area(
        "Paste a TaskSpec JSON",
        height=200,
        placeholder='{"task_id": "...", "description": "...", "function_signature": "...", "test_code": "..."}',
    )

st.divider()

# ── Run Button ───────────────────────────────────────────

run_col1, run_col2, run_col3 = st.columns([1, 2, 1])
with run_col2:
    run_clicked = st.button(
        "\U0001f680  Run Reflexion Agent",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.is_running,
    )

# ── Agent Execution ──────────────────────────────────────

if run_clicked:
    # Validate API key
    if not api_key:
        st.error("\u274c Please enter your API key in the sidebar.")
        st.stop()

    # Build task from form or JSON
    try:
        if json_input and json_input.strip():
            raw = json.loads(json_input)
            task = TaskSpec(**raw)
        else:
            task = TaskSpec(
                task_id=task_id,
                description=description,
                function_signature=function_signature,
                test_code=test_code,
            )
    except Exception as e:
        st.error(f"\u274c Invalid task: {e}")
        st.stop()

    # Configure the LLM settings
    import os
    os.environ["MODEL_NAME"] = model_name
    os.environ["TEMPERATURE"] = str(temperature)
    os.environ["MAX_ITERATIONS"] = str(max_iterations)
    os.environ["EXECUTION_TIMEOUT_SECONDS"] = str(timeout)

    # Set API key based on model
    if "gemini" in model_name.lower():
        os.environ["GEMINI_API_KEY"] = api_key
    elif "claude" in model_name.lower() or "anthropic" in model_name.lower():
        os.environ["ANTHROPIC_API_KEY"] = api_key
    else:
        os.environ["OPENAI_API_KEY"] = api_key

    # Reload settings
    from app.core.config import Settings
    settings = Settings()

    # Run the agent with live UI updates
    st.session_state.is_running = True
    st.session_state.live_iterations = []

    store = ReflectionStore(settings.memory_storage_path)
    buffer = TrajectoryBuffer()
    prior_reflections = store.get_for_task(task.task_id)

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
                try:
                    code = generate_code(task, all_reflections)
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
