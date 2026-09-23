"""
Centralised configuration via Pydantic Settings.

Loads values from environment variables and a ``.env`` file.  Every knob
the agent exposes (model choice, iteration budget, timeouts, storage
paths) is governed here so there is a single source of truth.
"""

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

# Locate .env relative to project root (2 levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Immutable application configuration."""

    # -- LLM provider keys -------------------------------------------------
    openai_api_key: str | None = Field(default=None)
    anthropic_api_key: str | None = Field(default=None)
    gemini_api_key: str | None = Field(default=None)

    # -- Model selection ----------------------------------------------------
    model_name: str = Field(
        default="gemini/gemini-3.6-flash",
        description="Any model string accepted by LiteLLM",
    )
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)

    # -- Agent behaviour ----------------------------------------------------
    max_iterations: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum Actor->Evaluator->Reflector loops before giving up",
    )
    execution_timeout_seconds: int = Field(
        default=10,
        ge=1,
        le=120,
        description="Hard wall-clock timeout for each sandbox execution",
    )

    # -- Persistence --------------------------------------------------------
    memory_storage_path: Path = Field(default=Path("./data/reflections.json"))

    model_config = {
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def inject_api_keys(self) -> None:
        """Push API keys into os.environ so LiteLLM can discover them."""
        if self.gemini_api_key:
            os.environ.setdefault("GEMINI_API_KEY", self.gemini_api_key)
        if self.openai_api_key:
            os.environ.setdefault("OPENAI_API_KEY", self.openai_api_key)
        if self.anthropic_api_key:
            os.environ.setdefault("ANTHROPIC_API_KEY", self.anthropic_api_key)


settings = Settings()
settings.inject_api_keys()
