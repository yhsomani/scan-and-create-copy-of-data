from __future__ import annotations

import re
from pathlib import Path
from typing import Generator, Optional, Tuple

ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")

# Extensions where ANSI escape codes are commonly found
ANSI_EXTENSIONS = {
    ".log", ".txt", ".out", ".err", ".ans", ".nfo",
}

# Encodings to try in order of preference
_ENCODING_CASCADE = ("utf-8", "utf-8-sig", "cp1252", "latin-1")


def strip_ansi(text: str) -> str:
    """Remove ANSI terminal escape sequences from text."""
    return ANSI_ESCAPE_RE.sub("", text)


def detect_encoding(path: Path, sample_size: int = 8192) -> str:
    """Detect file encoding by attempting multiple encodings on a sample.

    Reads the first ``sample_size`` bytes and tries each encoding in the
    cascade.  Returns the first encoding that decodes without error, or
    ``latin-1`` as a guaranteed fallback (latin-1 never raises).
    """
    try:
        raw = path.read_bytes()[:sample_size]
    except OSError:
        return "utf-8"

    for encoding in _ENCODING_CASCADE:
        try:
            raw.decode(encoding)
            return encoding
        except (UnicodeDecodeError, LookupError):
            continue

    # latin-1 is a superset of all single-byte values; should never fail
    return "latin-1"


# Safety limits for enterprise ingestion
MAX_LINE_LENGTH = 65536  # 64KB per line maximum


def read_text_lines(
    path: Path,
    encoding: Optional[str] = None,
    strip_ansi_codes: Optional[bool] = None,
    max_line_length: int = MAX_LINE_LENGTH,
) -> Generator[str, None, None]:
    """Yield lines from *path* with smart encoding detection and length protection.
    
    Uses a buffered chunked reader to prevent OOM on extremely long lines.
    """
    if encoding is None:
        encoding = detect_encoding(path)

    should_strip = strip_ansi_codes
    if should_strip is None:
        should_strip = path.suffix.lower() in ANSI_EXTENSIONS

    try:
        # We use a custom buffer to detect newlines without loading the whole line
        with path.open("r", encoding=encoding, errors="replace") as handle:
            buffer = ""
            while True:
                chunk = handle.read(16384) # 16KB chunks
                if not chunk:
                    if buffer:
                        yield _process_line(buffer, max_line_length, should_strip)
                    break
                
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    yield _process_line(line + "\n", max_line_length, should_strip)
                    
                # Protection: If the buffer exceeds 2x max_line_length without a newline,
                # we force a split to prevent memory overflow.
                if len(buffer) > max_line_length * 2:
                    yield _process_line(buffer[:max_line_length], max_line_length, should_strip)
                    buffer = buffer[max_line_length:]

    except (OSError, PermissionError):
        return

def _process_line(line: str, max_line_length: int, should_strip: bool) -> str:
    if len(line) > max_line_length:
        processed = line[:max_line_length] + " [TRUNCATED_LONG_LINE]\n"
    else:
        processed = line
    
    if should_strip:
        return strip_ansi(processed)
    return processed
