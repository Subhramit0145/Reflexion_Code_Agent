"""
Rich-powered structured logger.

Provides a pre-configured *console* (for direct Rich output) and a
stdlib *logger* routed through Rich so that every module in the project
gets consistent, colourful, timestamp-prefixed log lines.
"""

import logging

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

_THEME = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
        "reflection": "bold magenta",
        "iteration": "bold cyan",
        "code": "dim green",
    }
)

console = Console(theme=_THEME, highlight=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
)

logger = logging.getLogger("reflexion")
