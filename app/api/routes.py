"""
FastAPI REST endpoints.

Provides a POST /solve endpoint that accepts a TaskSpec, runs the
full Reflexion loop, and returns the AgentRun result as JSON.

Usage
-----
    uvicorn app.api.routes:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import settings
from app.core.schemas import AgentRun, TaskSpec
from app.agent.orchestrator import run_reflexion_loop
from app.memory.store import ReflectionStore

app = FastAPI(
    title="Reflexion Code Agent API",
    description=(
        "Autonomous Code Debugger & Test-Driven Fixer -- REST Interface. "
        "Submit a coding task and watch the agent iteratively solve it "
        "using verbal self-reflection."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared memory store (lives for the lifetime of the server process)
_store = ReflectionStore(settings.memory_storage_path)


@app.get("/health")
def health() -> dict:
    """Health check endpoint returning server status and active model."""
    return {
        "status": "ok",
        "model": settings.model_name,
        "max_iterations": settings.max_iterations,
        "memory_size": _store.size,
    }


class PromptRequest(BaseModel):
    prompt: str
    max_iterations: int | None = None


@app.post("/solve", response_model=AgentRun)
def solve(task: TaskSpec, max_iterations: int | None = None) -> AgentRun:
    """
    Solve a coding task using the Reflexion loop.

    Accepts a TaskSpec and returns the full AgentRun trajectory
    including all attempts, reflections, and the final outcome.
    """
    return run_reflexion_loop(task, _store, max_iterations=max_iterations)


@app.post("/solve-prompt", response_model=AgentRun)
def solve_prompt(request: PromptRequest) -> AgentRun:
    """
    Synthesize an executable specification and test suite from an arbitrary
    natural-language coding question, and solve it via the Reflexion loop.
    """
    from app.agent.synthesizer import synthesize_task_spec
    task = synthesize_task_spec(request.prompt)
    return run_reflexion_loop(task, _store, max_iterations=request.max_iterations)


@app.get("/reflections")
def list_reflections() -> dict:
    """Return the current contents of the episodic reflection store."""
    return {
        "count": _store.size,
        "reflections": [
            r.model_dump(mode="json") for r in _store._reflections
        ],
    }
