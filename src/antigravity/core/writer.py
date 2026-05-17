from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, TextIO

from antigravity.services.config import ScanConfig
from antigravity.utils.file_utils import ensure_directory


@dataclass
class WriterState:
    handle: TextIO
    part_number: int
    size_bytes: int
    entry_count: int
    output_path: Path
    ext_key: str


def normalize_extension(ext: str) -> str:
    if not ext:
        return "no_extension"
    return ext.lstrip(".").lower() or "no_extension"


class OutputLimitError(RuntimeError):
    pass


class SkippedLargeFileError(RuntimeError):
    pass


class OutputWriter:
    def __init__(self, config: ScanConfig) -> None:
        self.config = config
        self.states: Dict[str, WriterState] = {}
        self.output_files_created = 0
        self.index_entries: List[Dict] = []
        ensure_directory(self.config.output_dir)

    # ------------------------------------------------------------------
    # Streaming index – writes metadata incrementally instead of
    # accumulating in a list (fixes the memory-leak for huge repos).
    # ------------------------------------------------------------------



    # ------------------------------------------------------------------
    # Output path / header helpers
    # ------------------------------------------------------------------

    def build_output_path(self, part_number: int, ext_key: str = "") -> Path:
        ext = ".gz" if self.config.compress else ""
        # SPEC.md: ├── output_0.txt
        # We'll use 0-based naming for single/chunked as per SPEC
        idx = part_number - 1
        if self.config.mode == "single":
            return self.config.output_dir / f"output_{idx}.txt{ext}"
        if self.config.mode == "chunked":
            return self.config.output_dir / f"output_{idx}.txt{ext}"
        if ext_key:
            return self.config.output_dir / (
                f"{ext_key}.txt{ext}"
                if part_number == 1
                else f"{ext_key}_part_{part_number}.txt{ext}"
            )
        return self.config.output_dir / f"output_{idx}.txt{ext}"

    def build_header(self, part_number: int, ext_key: str = "") -> str:
        label = {"single": "SINGLE FILE", "chunked": "CHUNKED OUTPUT"}.get(
            self.config.mode, f"SCAN TYPE: .{ext_key}"
        )
        return (
            f"SCAN MODE: {label}\n"
            f"ROOT: {self.config.root}\n"
            f"PART: {part_number}\n"
            f"MAX OUTPUT FILES: {self.config.max_output_files}\n"
            f"MAX FILE SIZE PER OUTPUT: {self.config.max_chunk_mb} MB\n"
            + "=" * 80
            + "\n\n"
        )

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _check_disk_space(self, min_mb: int = 100) -> None:
        """Heuristic check to ensure we don't fill the disk."""
        try:
            import shutil
            total, used, free = shutil.disk_usage(self.config.output_dir)
            if free < min_mb * 1024 * 1024:
                raise OSError(f"INSUFFICIENT_DISK_SPACE: Less than {min_mb}MB remaining on {self.config.output_dir.drive}")
        except Exception:
            pass

    def open_state(
        self, writer_key: str, ext_key: str, part_number: int = 1
    ) -> WriterState:
        self._check_disk_space()
        
        if self.config.mode == "multi":
            if part_number > self.config.max_output_files:
                raise OutputLimitError(
                    f"Output file limit reached for extension {ext_key} ({self.config.max_output_files})"
                )
        else:
            if self.output_files_created >= self.config.max_output_files:
                raise OutputLimitError(
                    f"Output file limit reached ({self.config.max_output_files})"
                )
        
        output_path = self.build_output_path(part_number, ext_key)
        
        # Path Guard: Ensure we never write outside output_dir
        if not output_path.resolve().is_relative_to(self.config.output_dir.resolve()):
            raise ValueError(f"CRITICAL_SECURITY_VIOLATION: Output path escaped sandbox: {output_path}")

        if self.config.compress:
            handle = gzip.open(
                output_path.with_suffix(output_path.suffix + ".gz"),
                "wt",
                encoding="utf-8",
                errors="ignore",
            )
        else:
            handle = output_path.open(
                "w", encoding="utf-8", errors="ignore", buffering=8192
            )
        header = self.build_header(part_number, ext_key)
        handle.write(header)
        state = WriterState(
            handle=handle,
            part_number=part_number,
            size_bytes=len(header.encode("utf-8", errors="ignore")),
            entry_count=0,
            output_path=output_path,
            ext_key=ext_key,
        )
        self.states[writer_key] = state
        self.output_files_created += 1
        return state

    def _log_skipped_large(self, path: Path, entry_bytes: int) -> None:
        try:
            error_path = self.config.error_file
            ensure_directory(error_path.parent)
            with error_path.open("a", encoding="utf-8", errors="ignore") as handle:
                handle.write(
                    f"[SKIPPED TOO LARGE] {path}\n"
                    f"Entry size {entry_bytes} bytes exceeds max output file size budget "
                    f"({self.config.safe_chunk_bytes} bytes).\n\n"
                )
        except OSError as e:
            import logging
            logging.getLogger("scan").warning(f"Could not log skipped file: {e}")

    def get_writer_key(self, path: Path) -> tuple[str, str]:
        ext_key = normalize_extension(path.suffix.lower())
        if self.config.mode == "multi":
            return f"multi::{ext_key}", ext_key
        return self.config.mode, "" if self.config.mode != "multi" else ext_key

    # ------------------------------------------------------------------
    # Large-file splitting
    # ------------------------------------------------------------------

    def _split_write_large_entry(
        self,
        path: Path,
        relative_path: str,
        entry_chunks: List[str],
        metadata: Dict[str, object],
        writer_key: str,
        ext_key: str,
        state: WriterState,
    ) -> bool:
        """Write a file that exceeds ``safe_chunk_bytes`` by splitting its
        content across multiple output chunks with continuation markers."""
        budget = self.config.safe_chunk_bytes
        _SEP = "\u2550" * 64 + "\n"
        header_lines = [
            _SEP,
            f"FILE: {relative_path}\n",
            f"TYPE: {path.suffix.lower() or '(none)'}\n",
            f"SIZE: {metadata.get('size_bytes', 0)}\n",
            f"ENCODING: {metadata.get('encoding', 'utf-8')}\n",
            _SEP,
        ]
        footer = "\n"
        continuation_header = (
            _SEP
            + f"FILE (CONTINUED): {relative_path}\n"
            + _SEP
        )

        header_text = "".join(header_lines)
        header_bytes = len(header_text.encode("utf-8", errors="ignore"))
        footer_bytes = len(footer.encode("utf-8", errors="ignore"))
        cont_bytes = len(continuation_header.encode("utf-8", errors="ignore"))

        # Flatten content lines (skip the original header/separator already in chunks)
        content_lines: List[str] = []
        _sep_line = "\u2550" * 64
        for chunk in entry_chunks:
            stripped = chunk.rstrip("\n")
            if stripped == _sep_line:
                continue
            if chunk.startswith("FILE:") or chunk.startswith("TYPE:") or \
               chunk.startswith("SIZE:") or chunk.startswith("ENCODING:") or \
               chunk.startswith("FILE (CONTINUED):"):
                continue
            content_lines.append(chunk)

        part_index = 0
        line_idx = 0
        total_lines = len(content_lines)

        while line_idx < total_lines:
            # Decide if we need a new chunk file
            if part_index > 0 or (state.entry_count > 0 and state.size_bytes > 0):
                self.close_state(writer_key)
                state = self.open_state(
                    writer_key, ext_key, part_number=state.part_number + 1
                )

            # Write header or continuation header
            if part_index == 0:
                state.handle.write(header_text)
                state.size_bytes += header_bytes
                available = budget - state.size_bytes - footer_bytes
            else:
                state.handle.write(continuation_header)
                state.size_bytes += cont_bytes
                available = budget - state.size_bytes - footer_bytes

            # Fill this chunk with as many lines as possible
            written_in_part = 0
            while line_idx < total_lines and available > 0:
                line = content_lines[line_idx]
                line_bytes = len(line.encode("utf-8", errors="ignore"))
                if written_in_part > 0 and line_bytes > available:
                    break
                state.handle.write(line)
                state.size_bytes += line_bytes
                available -= line_bytes
                written_in_part += 1
                line_idx += 1

            state.handle.write(footer)
            state.size_bytes += footer_bytes
            state.entry_count += 1
            part_index += 1

        # Record metadata pointing to the last output file
        metadata.update(
            {
                "output_file": state.output_path.name,
                "part_number": state.part_number,
                "split_parts": part_index,
            }
        )

        return True

    # ------------------------------------------------------------------
    # Primary write path
    # ------------------------------------------------------------------

    def write_entry(
        self,
        path: Path,
        relative_path: str,
        entry_chunks: List[str],
        metadata: Dict[str, object],
    ) -> bool:
        writer_key, ext_key = self.get_writer_key(path)
        state = self.states.get(writer_key)
        if state is None:
            state = self.open_state(writer_key, ext_key)

        entry_text = "".join(entry_chunks)
        entry_bytes = len(entry_text.encode("utf-8", errors="ignore"))

        # ---- Large file that exceeds the entire chunk budget ----
        if entry_bytes > self.config.safe_chunk_bytes:
            if not self.config.allow_large_files:
                self._log_skipped_large(path, entry_bytes)
                return False
            return self._split_write_large_entry(
                path, relative_path, entry_chunks, metadata,
                writer_key, ext_key, state,
            )

        # ---- Normal rotation: current chunk is full ----
        if (
            self.config.mode != "chunked"
            or state.part_number <= self.config.max_output_files
        ):
            if (
                state.entry_count > 0
                and state.size_bytes + entry_bytes > self.config.safe_chunk_bytes
            ):
                self.close_state(writer_key)
                state = self.open_state(
                    writer_key, ext_key, part_number=state.part_number + 1
                )

        state.handle.write(entry_text)
        state.size_bytes += entry_bytes
        state.entry_count += 1

        metadata.update(
            {
                "output_file": state.output_path.name,
                "part_number": state.part_number,
            }
        )
        self.index_entries.append(metadata)

        return True

    def close_state(self, writer_key: str) -> None:
        state = self.states.get(writer_key)
        if not state:
            return
        try:
            state.handle.write("SCAN COMPLETED\n")
            state.handle.write(f"ENTRIES WRITTEN: {state.entry_count}\n")
            state.handle.close()
        finally:
            self.states.pop(writer_key, None)

    def finalize(self, metrics_summary: Optional[Dict] = None) -> None:
        for writer_key in list(self.states.keys()):
            self.close_state(writer_key)
        
        if not self.config.dry_run:
            self.write_indices(metrics_summary)

    def write_indices(self, summary: Optional[Dict] = None) -> None:
        """Generate index.json and index.md as per SPEC.md."""
        if not self.index_entries:
            return

        # 1. JSON Index
        index_data = {
            "summary": summary or {},
            "files": self.index_entries
        }
        try:
            with self.config.index_json.open("w", encoding="utf-8") as f:
                json.dump(index_data, f, indent=2)
        except Exception as e:
            import logging
            logging.getLogger("scan").error(f"Failed to write JSON index: {e}")

        # 2. Markdown Index
        try:
            with self.config.index_md.open("w", encoding="utf-8") as f:
                f.write("# Scan Index\n\n")
                if summary:
                    f.write("## Summary\n")
                    f.write(f"- **Files Processed**: {summary.get('files_processed', 0)}\n")
                    f.write(f"- **Bytes Processed**: {summary.get('bytes_processed', 0)}\n")
                    f.write(f"- **Duration**: {summary.get('elapsed_seconds', 0)}s\n\n")
                
                f.write("## File Listing\n\n")
                f.write("| File | Size | Type | Chunk |\n")
                f.write("| :--- | :--- | :--- | :--- |\n")
                for entry in self.index_entries:
                    rel = entry.get("relative_path", "unknown")
                    size = entry.get("size_bytes", 0)
                    ext = entry.get("extension", "unknown")
                    out = entry.get("output_file", "unknown")
                    f.write(f"| {rel} | {size} | {ext} | {out} |\n")
        except Exception as e:
            import logging
            logging.getLogger("scan").error(f"Failed to write Markdown index: {e}")
