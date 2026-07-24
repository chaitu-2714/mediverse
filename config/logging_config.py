"""MediVerse AI — Logging Configuration (Rich + Python logging)."""
from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

# ── Rich Console ─────────────────────────────────────────────
MEDIVERSE_THEME = Theme(
    {
        "logging.level.debug": "dim cyan",
        "logging.level.info": "bold green",
        "logging.level.warning": "bold yellow",
        "logging.level.error": "bold red",
        "logging.level.critical": "bold white on red",
        "repr.str": "cyan",
        "repr.number": "bold magenta",
    }
)

console = Console(theme=MEDIVERSE_THEME, stderr=True)


def setup_logging(
    log_level: str = "INFO",
    log_file: str = "./data/logs/mediverse.log",
    enable_rich: bool = True,
) -> None:
    """
    Configure application-wide logging with Rich console output and
    rotating file handler.
    """
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, log_level.upper(), logging.INFO)

    handlers: list[logging.Handler] = []

    # Rich console handler
    if enable_rich:
        rich_handler = RichHandler(
            console=console,
            rich_tracebacks=True,
            tracebacks_show_locals=False,
            show_time=True,
            show_level=True,
            show_path=True,
            markup=True,
        )
        rich_handler.setLevel(level)
        handlers.append(rich_handler)

    # Rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handlers.append(file_handler)

    # Root logger configuration
    logging.basicConfig(
        level=level,
        handlers=handlers,
        format="%(message)s",
        datefmt="[%X]",
        force=True,
    )

    # Silence noisy third-party loggers
    for noisy in [
        "httpx", "httpcore", "urllib3", "chromadb",
        "sentence_transformers", "transformers", "torch",
        "easyocr", "PIL", "matplotlib",
    ]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("mediverse").info(
        f"[bold green]MediVerse AI[/] logging initialized — level=[cyan]{log_level}[/]"
    )


def get_logger(name: str) -> logging.Logger:
    """Get a named logger under the mediverse namespace."""
    return logging.getLogger(f"mediverse.{name}")
