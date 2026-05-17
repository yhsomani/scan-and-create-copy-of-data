from pathlib import Path
from typing import Optional

from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt


def prompt_for_root() -> Path:
    raw = Prompt.ask("Enter absolute path of folder to scan").strip()
    if not raw:
        raise ValueError("Empty path provided.")
    return Path(raw.strip('"').strip("'")).expanduser().resolve()


def prompt_for_output_dir(default_root: Path) -> Path:
    default_str = str(default_root / "scan_output")
    raw = Prompt.ask("Enter output directory", default=default_str).strip()
    return Path(raw.strip('"').strip("'")).expanduser().resolve()


def prompt_for_mode() -> str:
    return Prompt.ask(
        "Select output mode",
        choices=["single", "multi", "chunked"],
        default="single"
    )


def prompt_for_format() -> str:
    return Prompt.ask(
        "Select index format",
        choices=["text", "json", "md"],
        default="text"
    )


def prompt_for_max_output_files() -> int:
    return IntPrompt.ask(
        "Enter maximum number of output files (0 for unlimited)",
        default=0
    )


def prompt_for_max_chunk_mb() -> float:
    return FloatPrompt.ask(
        "Enter maximum chunk size in MB (0 for unlimited)",
        default=0.0
    )


def prompt_for_config_mode() -> str:
    return Prompt.ask(
        "Configuration mode (1: Manual, 2: Auto-calc)",
        choices=["1", "2"],
        default="2"
    )


def prompt_for_ignore_file() -> str:
    return Prompt.ask("Enter ignore file name", default=".scanignore")


def prompt_for_cleanup() -> bool:
    return Confirm.ask("Delete created output files and logs after scan?", default=False)
