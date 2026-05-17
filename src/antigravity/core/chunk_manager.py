"""Chunk state tracking and partition decision logic.

This module is referenced in SPEC.md as ``core/chunk_manager.py``.  It
encapsulates the logic that decides *when* to rotate to a new output
file, keeping the chunking rules out of the main writer/scanner code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ChunkState:
    """Tracks the current state of a single output chunk."""

    part_number: int = 1
    size_bytes: int = 0
    entry_count: int = 0
    extensions_seen: Dict[str, int] = field(default_factory=dict)

    def record_entry(self, ext: str, entry_bytes: int) -> None:
        self.entry_count += 1
        self.size_bytes += entry_bytes
        self.extensions_seen[ext] = self.extensions_seen.get(ext, 0) + 1


class ChunkManager:
    """Decides whether the current chunk should be finalized and a new one
    started based on configurable size and file-count limits.

    Parameters
    ----------
    safe_chunk_bytes:
        Maximum usable bytes per chunk (after subtracting footer reserve).
    max_output_files:
        Hard upper bound on the number of output files that may be created.
    """

    def __init__(self, safe_chunk_bytes: int, max_output_files: int) -> None:
        self.safe_chunk_bytes = safe_chunk_bytes
        self.max_output_files = max_output_files
        self.current = ChunkState()
        self.history: List[ChunkState] = []

    # ------------------------------------------------------------------
    # Partition decision
    # ------------------------------------------------------------------

    def should_rotate(self, entry_bytes: int) -> bool:
        """Return ``True`` if adding an entry of *entry_bytes* would exceed
        the current chunk budget and a new chunk should be opened."""
        if self.current.entry_count == 0:
            return False
        return self.current.size_bytes + entry_bytes > self.safe_chunk_bytes

    def can_open_new_chunk(self) -> bool:
        """Return ``True`` if the output-file limit has not been reached."""
        total_chunks = len(self.history) + 1  # +1 for current
        return total_chunks < self.max_output_files

    def rotate(self) -> ChunkState:
        """Finalize the current chunk and start a new one.

        Returns the *new* ``ChunkState``.

        Raises
        ------
        RuntimeError
            If the output-file limit would be exceeded.
        """
        if not self.can_open_new_chunk():
            raise RuntimeError(
                f"Output file limit reached ({self.max_output_files})"
            )
        self.history.append(self.current)
        self.current = ChunkState(part_number=self.current.part_number + 1)
        return self.current

    def record(self, ext: str, entry_bytes: int) -> None:
        """Record that an entry was written to the current chunk."""
        self.current.record_entry(ext, entry_bytes)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def total_chunks_used(self) -> int:
        return len(self.history) + 1

    @property
    def total_bytes_written(self) -> int:
        return sum(c.size_bytes for c in self.history) + self.current.size_bytes

    @property
    def total_entries_written(self) -> int:
        return sum(c.entry_count for c in self.history) + self.current.entry_count

    def summary(self) -> Dict[str, object]:
        return {
            "total_chunks": self.total_chunks_used,
            "total_bytes": self.total_bytes_written,
            "total_entries": self.total_entries_written,
            "chunks": [
                {
                    "part": c.part_number,
                    "bytes": c.size_bytes,
                    "entries": c.entry_count,
                    "extensions": dict(c.extensions_seen),
                }
                for c in self.history + [self.current]
            ],
        }
