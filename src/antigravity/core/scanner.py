"""Core scanner module."""
from __future__ import annotations

import json
import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Generator, Iterable, List, Optional, Tuple

from antigravity.services.config import ScanConfig, MAX_WORKERS
from antigravity.core.filters import FileFilter
from antigravity.core.writer import OutputWriter
from antigravity.utils.file_utils import (
    normalize_path, ensure_directory, enumerate_files, safe_is_binary
)
from antigravity.utils.encoding_utils import detect_encoding, read_text_lines

logger = logging.getLogger("ScanEngine")




@dataclass
class FileStats:
    count: int = 0
    lines: int = 0
    bytes: int = 0


@dataclass
class ScanMetrics:
    files_scanned: int = 0
    files_processed: int = 0
    files_skipped: int = 0
    bytes_processed: int = 0
    lines_processed: int = 0
    errors: int = 0
    start_time: float = field(default_factory=time.monotonic)
    ext_stats: Dict[str, FileStats] = None

    def __post_init__(self):
        if self.ext_stats is None:
            self.ext_stats = {}

    def elapsed(self) -> float:
        return max(0.0, time.monotonic() - self.start_time)

    def add_file(self, ext: str, lines: int, bytes: int) -> None:
        if ext not in self.ext_stats:
            self.ext_stats[ext] = FileStats()
        self.ext_stats[ext].count += 1
        self.ext_stats[ext].lines += lines
        self.ext_stats[ext].bytes += bytes
        self.lines_processed += lines
        self.bytes_processed += bytes

    def summary(self) -> Dict[str, object]:
        return {
            "files_scanned": self.files_scanned,
            "files_processed": self.files_processed,
            "files_skipped": self.files_skipped,
            "bytes_processed": self.bytes_processed,
            "lines_processed": self.lines_processed,
            "errors": self.errors,
            "elapsed_seconds": round(self.elapsed(), 2),
            "ext_summary": self.ext_summary(),
        }

    def ext_summary(self) -> Dict[str, Dict[str, int]]:
        return {
            ext: {"count": s.count, "lines": s.lines, "bytes": s.bytes}
            for ext, s in self.ext_stats.items()
        }


class ProgressReporter:
    def __init__(self, total_files: int, total_bytes: int) -> None:
        self.total_files = total_files
        self.total_bytes = total_bytes
        self.start_time = time.monotonic()
        
        self.last_update_time = self.start_time
        self.last_processed = 0
        self.ema_rate = 0.0
        self.alpha = 0.2

    def format_eta(self, processed: int) -> str:
        current_time = time.monotonic()
        elapsed = current_time - self.last_update_time
        
        if processed == 0 or elapsed < 1e-6:
            if self.ema_rate > 0:
                return f"{int((self.total_files - processed) / self.ema_rate)}s"
            return "N/A"
            
        current_rate = (processed - self.last_processed) / elapsed
        
        if self.ema_rate == 0.0:
            self.ema_rate = current_rate
        else:
            self.ema_rate = (self.alpha * current_rate) + ((1 - self.alpha) * self.ema_rate)
            
        self.last_update_time = current_time
        self.last_processed = processed
        
        remaining = self.total_files - processed
        if self.ema_rate <= 0:
            return "N/A"
        return f"{int(remaining / self.ema_rate)}s"

    def report(self, processed_files: int, processed_bytes: int) -> str:
        percent = (
            (processed_bytes / self.total_bytes * 100) if self.total_bytes else 0.0
        )
        eta = self.format_eta(processed_files)
        return f"Progress: {processed_files}/{self.total_files} files ({percent:.1f}%), {processed_bytes} bytes, ETA {eta}"


class DirectoryScanner:
    def __init__(self, config: ScanConfig) -> None:
        self.config = config
        self.config.root = normalize_path(self.config.root)
        self.config.output_dir = normalize_path(self.config.output_dir)
        self.config.error_file = normalize_path(self.config.error_file)
        ensure_directory(self.config.output_dir)
        self.filter = FileFilter(self.config)
        self.writer = OutputWriter(self.config)
        self.metrics = ScanMetrics()
        self.state: Dict[str, object] = {}
        import re
        self.search_patterns = []
        for p in self.config.search_patterns:
            if p:
                try:
                    self.search_patterns.append(re.compile(p))
                except re.error as e:
                    self.logger.error(f"Invalid regex pattern '{p}': {e}")
        self._cached_candidates: Optional[List[Tuple[Path, int]]] = None
        self.logger = logging.getLogger("ScanEngine")

    def save_state(self, last_processed: str) -> None:
        if self.config.dry_run:
            return
        payload = {
            "root": str(self.config.root),
            "last_processed": last_processed,
            "mode": self.config.mode,
            "max_output_files": self.config.max_output_files,
            "max_chunk_mb": self.config.max_chunk_mb,
        }
        with self.config.state_file.open(
            "w", encoding="utf-8", errors="ignore"
        ) as handle:
            json.dump(payload, handle)

    def load_state(self) -> Optional[str]:
        if not self.config.resume or not self.config.state_file.exists():
            return None
        try:
            with self.config.state_file.open(
                "r", encoding="utf-8", errors="ignore"
            ) as handle:
                payload = json.load(handle)
            if payload.get("root") != str(self.config.root):
                return None
            return payload.get("last_processed")
        except (OSError, json.JSONDecodeError):
            return None

    def remove_state(self) -> None:
        try:
            if self.config.state_file.exists():
                self.config.state_file.unlink()
        except OSError as e:
            logger.warning(f"Could not remove state file: {e}")

    def estimate(self) -> Tuple[int, int]:
        if self._cached_candidates is not None:
            total_files = len(self._cached_candidates)
            total_bytes = sum(size for _, size in self._cached_candidates)
            return total_files, total_bytes

        candidates: List[Tuple[Path, int]] = []
        for path in self.enumerate_candidates():
            try:
                size = path.stat().st_size
                candidates.append((path, size))
            except OSError as e:
                logger.debug(f"Could not stat {path}: {e}")

        self._cached_candidates = candidates
        return len(candidates), sum(s for _, s in candidates)

    def enumerate_candidates(self) -> Generator[Path, None, None]:
        for path in enumerate_files(
            self.config.root,
            follow_links=self.config.follow_links,
            skip_directory=self.filter.should_skip_directory,
        ):
            yield path

    def cancel(self) -> None:
        self._abort = True
        self.logger.warning("SCAN_ABORT_SIGNAL_RECEIVED")

    def scan(self) -> ScanMetrics:
        self._abort = False
        self.metrics.start_time = time.monotonic()
        last_processed = self.load_state()
        skip_until = bool(last_processed)

        old_cache = self._load_cache()
        new_cache = {}

        need_estimate = (
            self.config.progress
            or self.config.resume
            or self.config.auto_calc
        )

        if self.config.auto_calc and self.config.mode in ["single", "chunked"]:
            self.logger.info("Auto-calculating output partitions...")
            _, total_bytes = self.estimate()
            safe_bytes = self.config.safe_chunk_bytes
            if total_bytes > 0 and safe_bytes > 0:
                self.config.max_output_files = max(1, (total_bytes + safe_bytes - 1) // safe_bytes)
                self.logger.info(f"Auto-calc: set max_output_files to {self.config.max_output_files}")

        if self._cached_candidates is not None:
            all_candidates = self._cached_candidates
            total_files = len(all_candidates)
            total_bytes = sum(s for _, s in all_candidates)
        elif need_estimate:
            total_files, total_bytes = self.estimate()
            all_candidates = self._cached_candidates
        else:
            all_candidates = [(p, 0) for p in self.enumerate_candidates()]
            total_files = len(all_candidates)
            total_bytes = 0

        reporter = (
            ProgressReporter(total_files, total_bytes) if self.config.progress else None
        )

        file_queue: List[Tuple[Path, str]] = []
        for path, file_size in all_candidates:
            if self._abort: break
            self.metrics.files_scanned += 1
            relative_path = path.relative_to(self.config.root).as_posix()
            
            if skip_until:
                if relative_path == last_processed:
                    skip_until = False
                else:
                    continue
            if not self.filter.should_process_file(path):
                self.metrics.files_skipped += 1
                continue

            if self.config.incremental:
                try:
                    mtime = path.stat().st_mtime
                except OSError:
                    mtime = 0.0
                new_cache[str(path)] = {"mtime": mtime, "size": file_size}
                cached = old_cache.get(str(path))
                if cached and cached.get("mtime") == mtime and cached.get("size") == file_size:
                    self.metrics.files_skipped += 1
                    continue

            file_queue.append((path, relative_path))

        workers = max(1, min(self.config.workers, MAX_WORKERS))
        processed_files = 0
        all_matches = {}

        for path, relative_path, entry_chunks, line_count, file_size, encoding, exc, matches in self._generate_results(file_queue, workers):
            if self._abort:
                self.logger.warning("Scan aborted by user.")
                break
                
            if exc is not None:
                from antigravity.core.writer import OutputLimitError
                if isinstance(exc, OutputLimitError):
                    self.logger.warning(f"Output limit reached: {exc}")
                    self.log_error(path, exc)
                    break
                self.metrics.errors += 1
                self.logger.error(f"Error processing {path}: {exc}")
                self.log_error(path, exc)
                continue

            try:
                if matches:
                    all_matches[relative_path] = matches
                metadata = self.extract_metadata(
                    path, relative_path, file_size, line_count, encoding
                )
                if matches:
                    metadata["search_matches"] = matches
                if not self.config.dry_run:
                    written = self.writer.write_entry(
                        path, relative_path, entry_chunks, metadata
                    )
                    if not written:
                        self.metrics.files_skipped += 1
                    else:
                        self.metrics.files_processed += 1
                        ext = path.suffix.lower() or ".no_ext"
                        self.metrics.add_file(ext, line_count, file_size)
                else:
                    self.metrics.files_processed += 1
                    ext = path.suffix.lower() or ".no_ext"
                    self.metrics.add_file(ext, line_count, file_size)
                
                processed_files += 1
                if self.config.resume and processed_files % 50 == 0:
                    self.save_state(relative_path)
                
                if self.config.progress and reporter and processed_files % 10 == 0:
                    self.logger.info(reporter.report(processed_files, self.metrics.bytes_processed))
                elif self.config.verbose:
                    self.logger.info(f"Processed: {relative_path}")
                    
            except Exception as write_exc:
                from antigravity.core.writer import OutputLimitError
                if isinstance(write_exc, OutputLimitError):
                    self.logger.warning(f"Output limit reached: {write_exc}")
                    self.log_error(path, write_exc)
                    break
                self.metrics.errors += 1
                self.logger.error(f"Write error for {path}: {write_exc}")
                self.log_error(path, write_exc)
                continue

        summary_data = self.metrics.summary()
        if all_matches:
            summary_data["search_matches"] = all_matches

        self.writer.finalize(summary_data)
        if not self.config.dry_run:
            self.write_scan_summary(summary_data)
            if self.config.incremental:
                self._save_cache(new_cache)
        

            
        if self.config.resume:
            self.remove_state()
        return self.metrics

    def _generate_results(self, file_queue: List[Tuple[Path, str]], workers: int) -> Generator[Tuple[Path, str, List[str], int, int, str, Optional[Exception], Dict[str, List[int]]], None, None]:
        mem_limit = max(1, workers * 2)
        
        if workers > 1:
            from concurrent.futures import as_completed
            BATCH = 256
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for i in range(0, len(file_queue), BATCH):
                    batch = file_queue[i:i+BATCH]
                    futures = {pool.submit(self._process_single_file, p, rp): (p, rp) for p, rp in batch}
                    for future in as_completed(futures):
                        yield future.result()
        else:
            for p, rp in file_queue:
                yield self._process_single_file(p, rp)

    def _process_single_file(self, path: Path, relative_path: str) -> Tuple[Path, str, List[str], int, int, str, Optional[Exception], Dict[str, List[int]]]:
        try:
            try:
                file_size = path.stat().st_size
            except OSError:
                file_size = 0

            if safe_is_binary(path):
                return path, relative_path, [], 0, file_size, "binary", None, {}

            entry_chunks, line_count, encoding, matches = self.build_entry_chunks(path, relative_path)
            
            return path, relative_path, entry_chunks, line_count, file_size, encoding, None, matches
        except Exception as e:
            return path, relative_path, [], 0, 0, "", e, {}

    _SEPARATOR = "═" * 64 + "\n"

    def build_entry_chunks(
        self, path: Path, relative_path: str
    ) -> Tuple[List[str], int, str, Dict[str, List[int]]]:
        ext = path.suffix.lower() or "(none)"
        try:
            file_size = path.stat().st_size
        except OSError:
            file_size = 0
        encoding = detect_encoding(path)

        chunks: List[str] = [
            self._SEPARATOR,
            f"FILE: {relative_path}\n",
            f"TYPE: {ext}\n",
            f"SIZE: {file_size}\n",
            f"ENCODING: {encoding}\n",
            self._SEPARATOR,
        ]
        line_count = 0
        content_buffer = []
        matches: Dict[str, List[int]] = {pat.pattern: [] for pat in self.search_patterns}
        
        for line in read_text_lines(path, encoding=encoding):
            content_buffer.append(line)
        
        full_content = "".join(content_buffer)
        processed_lines = full_content.splitlines(keepends=True)
        for i, line in enumerate(processed_lines, 1):
            chunks.append(line)
            line_count += 1
            for pat in self.search_patterns:
                if pat.search(line):
                    matches[pat.pattern].append(i)
                    
        # Remove patterns with no matches
        matches = {k: v for k, v in matches.items() if v}
            
        chunks.append("\n")
        return chunks, line_count, encoding, matches

    def extract_metadata(
        self, path: Path, relative_path: str, size_bytes: int, line_count: int, encoding: str
    ) -> Dict[str, object]:
        return {
            "relative_path": relative_path,
            "absolute_path": str(path),
            "size_bytes": size_bytes,
            "lines": line_count,
            "extension": path.suffix.lower(),
            "encoding": encoding,
        }

    def write_scan_summary(self, summary_data: Dict[str, object] = None) -> None:
        summary_path = self.config.output_dir / "summary.json"
        try:
            with summary_path.open("w", encoding="utf-8", errors="ignore") as fh:
                json.dump(summary_data or self.metrics.summary(), fh, indent=2)
        except OSError as e:
            self.log_error(summary_path, e)

    def log_error(self, path: Path, error: Exception) -> None:
        try:
            error_path = self.config.error_file
            ensure_directory(error_path.parent)
            with error_path.open("a", encoding="utf-8", errors="ignore") as handle:
                handle.write(f"[FILE_ERROR] {path}\n{type(error).__name__}: {error}\n")
        except OSError as e:
            import sys
            print(f"[FILE_ERROR] {path}: {error}", file=sys.stderr)

    def _load_cache(self) -> Dict[str, Dict[str, float]]:
        if not self.config.incremental or not self.config.cache_file.exists():
            return {}
        try:
            with self.config.cache_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_cache(self, new_cache: Dict[str, Dict[str, float]]) -> None:
        if not self.config.incremental:
            return
        try:
            ensure_directory(self.config.cache_file.parent)
            with self.config.cache_file.open("w", encoding="utf-8") as f:
                json.dump(new_cache, f, indent=2)
        except Exception as e:
            self.log_error(self.config.cache_file, e) as the compatible adapter class at the top