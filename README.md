# 🔁 Reflexion Code Agent

**Autonomous Code Debugger & Test-Driven Fixer** powered by Verbal Reinforcement Learning without Weight Updates.

[![CI](https://github.com/Subhramit0145/Reflexion_Code_Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Subhramit0145/Reflexion_Code_Agent/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![LiteLLM](https://img.shields.io/badge/LLM-LiteLLM-orange.svg)](https://github.com/BerriAI/litellm)

---

## 🧠 What is Reflexion?

**Reflexion** ([Shinn et al., NeurIPS 2023](https://arxiv.org/abs/2303.11366)) is a framework that enables LLM agents to **learn from their mistakes** through verbal self-reflection — without any gradient updates or fine-tuning.

Traditional RL updates model weights after failure. Reflexion instead:

1. **Attempts** a task (generates code)
2. **Evaluates** the result (executes tests in a sandbox)
3. **Reflects** on failures (verbal self-critique via LLM)
4. **Retries** with accumulated insights injected as context

This creates a powerful feedback loop where the agent genuinely improves across iterations — using only natural language as the reinforcement signal.

> *"The key insight is that verbal reinforcement can provide a more nuanced and expressive form of feedback than scalar rewards."* — Shinn et al.

---

## 🏗️ System Architecture

```
                          ┌─────────────────────────────────────────────┐
                          │              ORCHESTRATOR                    │
                          │                                             │
  ┌──────────┐            │  ┌──────────┐   ┌───────────┐   ┌────────┐ │
  │   Task   │───────────▶│  │  ACTOR   │──▶│ EVALUATOR │──▶│REFLECT │ │
  │  + Tests │            │  │(LLM Gen) │   │ (Sandbox) │   │  (LLM) │ │
  └──────────┘            │  └────▲─────┘   └─────┬─────┘   └───┬────┘ │
                          │       │               │              │      │
                          │       │   ┌───────────┘     ┌────────┘      │
                          │       │   │ Pass?           │ Verbal        │
                          │       │   │                 │ Critique      │
                          │       │   ▼                 ▼               │
                          │  ┌────┴──────────────────────────────┐      │
                          │  │         EPISODIC MEMORY           │      │
                          │  │  (Short-Term Buffer + Long-Term   │      │
                          │  │   JSON-backed Reflection Store)   │      │
                          │  └───────────────────────────────────┘      │
                          │                                             │
                          │         ┌──────────┐                        │
                          │         │  OUTPUT   │  Solved code +        │
                          │         │  + Report │  trajectory log       │
                          │         └──────────┘                        │
                          └─────────────────────────────────────────────┘
```

### Component Breakdown

| Component | Module | Description |
|-----------|--------|-------------|
| **Actor** | `app/agent/actor.py` | Prompts an LLM to generate Python code, injecting prior reflections as lessons learned |
| **Evaluator** | `app/agent/evaluator.py` | Executes candidate code + test suite in an isolated subprocess sandbox |
| **Reflector** | `app/agent/reflector.py` | Analyses failed trajectories — produces verbal self-critiques with failure categorisation |
| **Orchestrator** | `app/agent/orchestrator.py` | Drives the iterative Actor→Evaluator→Reflector loop with configurable stopping conditions |
| **Memory** | `app/memory/` | Short-term trajectory buffer + persistent JSON-backed episodic store with keyword retrieval |
| **Sandbox** | `app/sandbox/runner.py` | Isolated subprocess runner with timeout enforcement, stdout/stderr capture, test-count parsing |
| **CLI** | `app/cli.py` | Rich interactive terminal with coloured output, syntax highlighting, and reflection trail |
| **API** | `app/api/routes.py` | FastAPI REST endpoints (`/solve`, `/health`, `/reflections`) with auto-generated docs |

---

## ✨ Key Features

- 🔄 **Self-Correcting Loop** — Agent iteratively improves via verbal reflection, not weight updates
- 🧪 **Sandboxed Execution** — Code runs in isolated subprocesses with hard timeouts
- 🧠 **Episodic Memory** — Reflections persist across tasks for cross-problem learning
- 🎨 **Rich CLI** — Coloured terminal output with syntax-highlighted solutions and reflection trails
- 🌐 **REST API** — FastAPI server with auto-docs at `/docs` for headless integration
- 📊 **Benchmark Suite** — 6 curated problems comparing Baseline vs. Reflexion with results table
- 🔌 **Multi-Provider LLM** — Works with OpenAI, Anthropic, Gemini, Groq, Ollama via LiteLLM
- 🐳 **Docker Ready** — One-command deployment with `docker compose up`
- ✅ **Fully Tested** — 33 unit + integration tests with mocked LLM calls (no API key needed)
- 🔁 **CI/CD Pipeline** — GitHub Actions testing across Python 3.10, 3.11, 3.12

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- An API key for at least one LLM provider (OpenAI, Anthropic, Gemini, etc.)

### Installation

```bash
# Clone the repository
git clone https://github.com/Subhramit0145/Reflexion_Code_Agent.git
cd Reflexion_Code_Agent

# Create a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Configure your API key
cp .env.example .env
# Edit .env and set at least one API key + your preferred model
```

### Run the Demo

```bash
# Interactive CLI with built-in Fibonacci demo
python -m app.cli

# Custom task from a JSON file
python -m app.cli --task-file examples/my_task.json

# Override iteration budget
python -m app.cli --max-iterations 5
```

### Custom Task JSON Format

```json
{
  "task_id": "my-custom-task",
  "description": "Implement a function that reverses a string.",
  "function_signature": "def reverse_string(s: str) -> str:",
  "test_code": "assert reverse_string('hello') == 'olleh'\nassert reverse_string('') == ''\nprint('2 passed')"
}
```

### REST API

```bash
# Start the API server
uvicorn app.api.routes:app --reload

# Interactive docs
# Open http://localhost:8000/docs in your browser

# Solve a task via curl
curl -X POST http://localhost:8000/solve \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "api-test",
    "description": "Return the square of a number.",
    "function_signature": "def square(n: int) -> int:",
    "test_code": "assert square(3) == 9\nassert square(0) == 0\nprint(\"2 passed\")"
  }'
```

### Docker

```bash
# Build and run with Docker Compose
docker compose up --build

# API available at http://localhost:8000
# Auto-docs at http://localhost:8000/docs
```

---

## 🖥️ Web UI (Streamlit)

A full interactive web interface is included for visual, no-terminal-needed usage.

`ash
streamlit run web/streamlit_app.py
# Opens at http://localhost:8501
`

**Features:**
- Example task picker with 5 built-in problems
- Sidebar config: model, API key, iterations, temperature, timeout
- Live iteration view: watch code generation, testing, and self-reflection in real time
- Metrics dashboard: iterations, duration, reflections count, pass/fail
- Syntax-highlighted final solution
- Full reflection trail visualization

---

## 📊 Benchmark Results

Comparison of **Baseline** (single-shot, no reflection) vs. **Reflexion** (3 iterations with self-reflection) on 6 curated problems:

| Problem | Baseline (1-shot) | Reflexion (3 iter) | Iterations Used |
|---------|:-----------------:|:------------------:|:---------------:|
| Two Sum | ❌ | ✅ | 2 |
| Is Palindrome | ✅ | ✅ | 1 |
| Max Subarray | ❌ | ✅ | 3 |
| Valid Parentheses | ✅ | ✅ | 1 |
| FizzBuzz | ✅ | ✅ | 1 |
| Flatten Nested | ❌ | ✅ | 2 |
| **Total** | **3/6 (50%)** | **6/6 (100%)** | — |

> 🚀 **Reflexion solved 3 more problems (+50% improvement)**
>
> *Results from a typical run with `gpt-4o-mini` at `temperature=0.2`. Actual results may vary by model and run.*

### Run Benchmarks Yourself

```bash
python -m benchmarks.run_eval --max-iterations 3
```

---

## ⚙️ Configuration

All settings are controlled via environment variables or `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_NAME` | `gpt-4o-mini` | Any [LiteLLM-compatible](https://docs.litellm.ai/docs/providers) model string |
| `MAX_ITERATIONS` | `3` | Maximum Reflexion loop iterations before giving up |
| `EXECUTION_TIMEOUT_SECONDS` | `10` | Sandbox timeout per code execution (seconds) |
| `TEMPERATURE` | `0.2` | LLM sampling temperature |
| `MEMORY_STORAGE_PATH` | `./data/reflections.json` | Episodic memory persistence location |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `GEMINI_API_KEY` | — | Google Gemini API key |

### Example Model Strings

```bash
MODEL_NAME=gpt-4o-mini                    # OpenAI
MODEL_NAME=claude-sonnet-4-20250514          # Anthropic
MODEL_NAME=gemini/gemini-2.0-flash         # Google Gemini
MODEL_NAME=groq/llama-3.1-70b-versatile   # Groq
MODEL_NAME=ollama/llama3                   # Local Ollama
```

---

## 🧪 Testing

```bash
# Run full test suite (no API key required — LLM calls are mocked)
pytest tests/ -v

# Run only sandbox tests
pytest tests/test_sandbox.py -v

# Run only memory tests
pytest tests/test_memory.py -v

# Run orchestrator integration tests
pytest tests/test_orchestrator.py -v
```

---

## 📁 Project Structure

```
reflexion-code-agent/
├── app/
│   ├── __init__.py             # Package metadata
│   ├── __main__.py             # python -m app entry point
│   ├── cli.py                  # Rich interactive CLI
│   ├── core/
│   │   ├── config.py           # Pydantic Settings (single source of truth)
│   │   ├── logger.py           # Rich-powered structured logging
│   │   └── schemas.py          # All Pydantic data models
│   ├── agent/
│   │   ├── actor.py            # LLM code generation with reflection injection
│   │   ├── evaluator.py        # Test execution interface
│   │   ├── reflector.py        # Verbal self-critique engine
│   │   └── orchestrator.py     # Iterative Reflexion loop controller
│   ├── memory/
│   │   ├── buffer.py           # Short-term trajectory buffer
│   │   └── store.py            # Persistent episodic reflection store
│   ├── sandbox/
│   │   └── runner.py           # Isolated subprocess executor
│   └── api/
│       └── routes.py           # FastAPI REST endpoints
├── benchmarks/
│   ├── problems.py             # 6 curated coding problems
│   └── run_eval.py             # Baseline vs. Reflexion comparison
├── tests/
│   ├── test_sandbox.py         # Sandbox runner tests (14 cases)
│   ├── test_memory.py          # Memory subsystem tests (14 cases)
│   └── test_orchestrator.py    # Integration tests with mocked LLM (5 cases)
├── .github/workflows/
│   └── ci.yml                  # GitHub Actions CI pipeline
├── Dockerfile                  # Multi-stage container image
├── docker-compose.yml          # One-command deployment
├── pyproject.toml              # Python packaging & tool config
├── requirements.txt            # Dependency list
├── .env.example                # Configuration template
├── LICENSE                     # MIT License
└── README.md                   # This file
```

---

## 🎓 How It Works — The Reflexion Loop

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  Iteration 1:                                                       │
│    Actor generates code ──► Evaluator runs tests ──► ❌ FAIL        │
│    Reflector: "Used addition instead of multiplication.             │
│               Fix by replacing + with *."                           │
│    ──► Reflection saved to episodic memory                          │
│                                                                     │
│  Iteration 2:                                                       │
│    Actor sees reflection ──► generates improved code                │
│    Evaluator runs tests ──► ❌ FAIL                                 │
│    Reflector: "Fixed multiplication but forgot edge case n=0.       │
│               Add a guard clause for zero."                         │
│    ──► Reflection saved to episodic memory                          │
│                                                                     │
│  Iteration 3:                                                       │
│    Actor sees both reflections ──► generates further improved code  │
│    Evaluator runs tests ──► ✅ ALL TESTS PASS                      │
│    ──► 🎉 Task solved!                                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📝 References

- Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K., & Yao, S. (2023).
  **Reflexion: Language Agents with Verbal Reinforcement Learning.**
  *Advances in Neural Information Processing Systems (NeurIPS 2023).*
  [arXiv:2303.11366](https://arxiv.org/abs/2303.11366)

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤️ as a portfolio project demonstrating autonomous AI agent design,
  iterative self-correction, and production-grade Python engineering.
</p>
