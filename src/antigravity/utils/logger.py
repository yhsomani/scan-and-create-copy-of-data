import logging
import sys
from pathlib import Path
from rich.logging import RichHandler

def setup_logger(name: str = "antigravity", log_dir: Path | None = None, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if logger.hasHandlers():
        logger.handlers.clear()

    # Console Handler (Rich)
    console_handler = RichHandler(rich_tracebacks=True, markup=True)
    console_handler.setLevel(level)
    console_format = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File Handler
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "antigravity.log", mode="a", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    return logger

logger = setup_logger()
