"""
Persistent episodic reflection store.

Saves reflections to a JSON file so the agent can recall failure
patterns across *different* tasks -- not just within the current
episode.  This is the long-term memory component of Reflexion.

In a production system this layer would be backed by a vector database
(ChromaDB / Pinecone) for semantic retrieval.  Here we use a simple
JSON file with keyword search to keep dependencies minimal while
demonstrating the architectural pattern.
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from app.core.logger import logger
from app.core.schemas import Reflection


class ReflectionStore:
    """Thread-safe, file-backed episodic reflection storage."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = Lock()
        self._reflections: list[Reflection] = []
        self._load()

    # -- Persistence -------------------------------------------------------

    def _load(self) -> None:
        """Load existing reflections from disk."""
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                self._reflections = [Reflection(**r) for r in raw]
                logger.info(f"Loaded {len(self._reflections)} reflections from {self._path}")
            except (json.JSONDecodeError, Exception) as exc:
                logger.warning(f"Could not load reflections: {exc}. Starting fresh.")
                self._reflections = []

    def _save(self) -> None:
        """Flush all reflections to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [r.model_dump(mode="json") for r in self._reflections]
        self._path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    # -- Public API --------------------------------------------------------

    def add(self, reflection: Reflection) -> None:
        """Persist a new reflection."""
        with self._lock:
            self._reflections.append(reflection)
            self._save()
            logger.info(
                f"Stored reflection for task={reflection.task_id} "
                f"iter={reflection.iteration} ({reflection.failure_category})"
            )

    def get_for_task(self, task_id: str) -> list[Reflection]:
        """Return all reflections associated with a specific task."""
        with self._lock:
            return [r for r in self._reflections if r.task_id == task_id]

    def search(self, query: str, top_k: int = 3) -> list[Reflection]:
        """
        Simple keyword-based retrieval.

        Scores each reflection by how many query tokens appear in its
        content.  In a production system, replace this with a vector
        similarity search.
        """
        query_tokens = set(query.lower().split())
        scored: list[tuple[float, Reflection]] = []
        with self._lock:
            for ref in self._reflections:
                ref_tokens = set(ref.content.lower().split())
                overlap = len(query_tokens & ref_tokens)
                if overlap > 0:
                    scored.append((overlap, ref))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ref for _, ref in scored[:top_k]]

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._reflections)
