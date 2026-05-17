import json
import os
import tempfile
import unittest
from pathlib import Path

from antigravity.services.config import ScanConfig
from antigravity.core.scanner import DirectoryScanner
from antigravity.core.filters import FileFilter, SKIP_DIRS, USEFUL_EXTENSIONS, MAX_FILE_SIZE_BYTES
from antigravity.core.writer import OutputWriter, normalize_extension
from antigravity.core.chunk_manager import ChunkManager
from antigravity.utils.encoding_utils import detect_encoding, strip_ansi, read_text_lines


# =========================================================================
# Scanner Tests
# =========================================================================

class TestDirectoryScanner(unittest.TestCase):
    def test_directory_scanner_dry_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sample_file = root / "example.py"
            sample_file.write_text('print("hello")\n', encoding="utf-8")

            output_dir = root / "scan_output"
            config = ScanConfig(
                root=root,
                output_dir=output_dir,
                error_file=output_dir / "error.log",
                mode="single",
                output_format="text",
                max_output_files=2,
                max_chunk_mb=1.0,
                dry_run=True,
                resume=False,
                progress=False,
                verbose=False,
            )

            scanner = DirectoryScanner(config)
            metrics = scanner.scan()

            self.assertEqual(metrics.files_processed, 1)
            self.assertEqual(metrics.files_skipped, 0)
            self.assertEqual(metrics.errors, 0)
            self.assertTrue(output_dir.exists())
            self.assertFalse((output_dir / "all_files.txt").exists())

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "scan_output"
            config = ScanConfig(
                root=root,
                output_dir=output_dir,
                error_file=output_dir / "error.log",
                mode="single",
                max_output_files=2,
                max_chunk_mb=1.0,
                dry_run=True,
                progress=False,
            )

            scanner = DirectoryScanner(config)
            metrics = scanner.scan()

            self.assertEqual(metrics.files_processed, 0)
            self.assertEqual(metrics.files_scanned, 0)

    def test_binary_file_skipped(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary_file = root / "image.png"
            binary_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00")

            config = ScanConfig(
                root=root,
                output_dir=root / "scan_output",
                error_file=root / "error.log",
                mode="single",
                max_chunk_mb=1.0,
                dry_run=True,
                progress=False,
            )

            scanner = DirectoryScanner(config)
            metrics = scanner.scan()

            self.assertEqual(metrics.files_processed, 0)
            self.assertEqual(metrics.files_skipped, 1)

    def test_hidden_file_skipped(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            hidden_file = root / ".hidden.py"
            hidden_file.write_text("# secret", encoding="utf-8")

            config = ScanConfig(
                root=root,
                output_dir=root / "scan_output",
                error_file=root / "error.log",
                mode="single",
                max_chunk_mb=1.0,
                skip_hidden=True,
                dry_run=True,
                progress=False,
            )

            scanner = DirectoryScanner(config)
            metrics = scanner.scan()

            self.assertEqual(metrics.files_skipped, 1)

    def test_hidden_file_included(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            hidden_file = root / ".hidden.py"
            hidden_file.write_text("# secret", encoding="utf-8")

            config = ScanConfig(
                root=root,
                output_dir=root / "scan_output",
                error_file=root / "error.log",
                mode="single",
                max_chunk_mb=1.0,
                skip_hidden=False,
                dry_run=True,
                progress=False,
            )

            scanner = DirectoryScanner(config)
            metrics = scanner.scan()

            self.assertEqual(metrics.files_processed, 1)

    def test_nested_directories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            subdir = root / "src" / "core"
            subdir.mkdir(parents=True)
            (subdir / "module.py").write_text("def foo(): pass", encoding="utf-8")

            config = ScanConfig(
                root=root,
                output_dir=root / "scan_output",
                error_file=root / "error.log",
                mode="single",
                max_chunk_mb=1.0,
                dry_run=True,
                progress=False,
            )

            scanner = DirectoryScanner(config)
            metrics = scanner.scan()

            self.assertEqual(metrics.files_processed, 1)

    def test_chunked_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for i in range(10):
                (root / f"file{i}.py").write_text(
                    f"# file {i}\n" * 100, encoding="utf-8"
                )

            output_dir = root / "scan_output"
            config = ScanConfig(
                root=root,
                output_dir=output_dir,
                error_file=output_dir / "error.log",
                mode="chunked",
                max_output_files=2,
                max_chunk_mb=0.001,
                dry_run=True,
                progress=False,
            )

            scanner = DirectoryScanner(config)
            metrics = scanner.scan()

            self.assertEqual(metrics.files_processed, 10)

    def test_multi_extension_grouping(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "main.py").write_text("# py", encoding="utf-8")
            (root / "test.py").write_text("# py", encoding="utf-8")
            (root / "style.css").write_text("/* css */", encoding="utf-8")

            config = ScanConfig(
                root=root,
                output_dir=root / "scan_output",
                error_file=root / "error.log",
                mode="multi",
                max_chunk_mb=1.0,
                dry_run=True,
                progress=False,
            )

            scanner = DirectoryScanner(config)
            metrics = scanner.scan()

            self.assertEqual(metrics.files_processed, 3)

    def test_metrics_ext_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.py").write_text("line1\nline2\nline3", encoding="utf-8")
            (root / "b.js").write_text("x", encoding="utf-8")

            config = ScanConfig(
                root=root,
                output_dir=root / "scan_output",
                error_file=root / "error.log",
                mode="single",
                max_chunk_mb=1.0,
                dry_run=True,
                progress=False,
            )

            scanner = DirectoryScanner(config)
            metrics = scanner.scan()

            self.assertEqual(metrics.files_processed, 2)
            self.assertIn(".py", metrics.ext_stats)
            self.assertIn(".js", metrics.ext_stats)

    def test_config_from_dict(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = ScanConfig.from_dict({"root": str(root)}, base_path=root)
            self.assertEqual(config.root, root.resolve())

    def test_config_missing_root(self):
        with self.assertRaises(ValueError):
            ScanConfig.from_dict({}, base_path=Path.cwd())

    def test_config_nonexistent_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(FileNotFoundError):
                ScanConfig.from_dict(
                    {"root": "/nonexistent/path"}, base_path=Path(temp_dir)
                )

    def test_spec_compliant_headers_in_output(self):
        """Verify the output uses ═ separators and includes TYPE/SIZE/ENCODING."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "hello.py").write_text("print(1)\n", encoding="utf-8")

            output_dir = root / "scan_output"
            config = ScanConfig(
                root=root,
                output_dir=output_dir,
                error_file=output_dir / "error.log",
                mode="single",
                max_output_files=5,
                max_chunk_mb=10.0,
                dry_run=False,
                progress=False,
            )

            scanner = DirectoryScanner(config)
            scanner.scan()

            output_file = output_dir / "output_0.txt"
            self.assertTrue(output_file.exists())
            content = output_file.read_text(encoding="utf-8")
            self.assertIn("\u2550" * 64, content)
            self.assertIn("FILE: hello.py", content)
            self.assertIn("TYPE: .py", content)
            self.assertIn("SIZE:", content)
            self.assertIn("ENCODING:", content)

    def test_summary_json_written(self):
        """Verify summary.json is generated after a real scan."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "app.py").write_text("x = 1\n", encoding="utf-8")

            output_dir = root / "scan_output"
            config = ScanConfig(
                root=root,
                output_dir=output_dir,
                error_file=output_dir / "error.log",
                mode="single",
                max_output_files=5,
                max_chunk_mb=10.0,
                dry_run=False,
                progress=False,
            )

            scanner = DirectoryScanner(config)
            scanner.scan()

            summary_file = output_dir / "summary.json"
            self.assertTrue(summary_file.exists())
            data = json.loads(summary_file.read_text(encoding="utf-8"))
            self.assertEqual(data["files_processed"], 1)
            self.assertIn("elapsed_seconds", data)

    def test_cached_estimate_avoids_double_traversal(self):
        """estimate() caches results so scan() reuses them."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.py").write_text("1", encoding="utf-8")

            config = ScanConfig(
                root=root,
                output_dir=root / "scan_output",
                error_file=root / "error.log",
                mode="single",
                max_chunk_mb=10.0,
                dry_run=True,
                progress=False,
            )

            scanner = DirectoryScanner(config)
            total_files, total_bytes = scanner.estimate()
            self.assertEqual(total_files, 1)
            self.assertIsNotNone(scanner._cached_candidates)

            # Second call should return same data from cache
            f2, b2 = scanner.estimate()
            self.assertEqual(f2, total_files)
            self.assertEqual(b2, total_bytes)


# =========================================================================
# Encoding Tests
# =========================================================================

class TestEncodingUtils(unittest.TestCase):
    def test_detect_utf8(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write("# hello world\n")
            path = Path(f.name)
        try:
            self.assertEqual(detect_encoding(path), "utf-8")
        finally:
            path.unlink()

    def test_detect_latin1_fallback(self):
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".txt", delete=False
        ) as f:
            # Byte 0xFF is invalid UTF-8 but valid latin-1
            f.write(b"caf\xe9\n")
            path = Path(f.name)
        try:
            enc = detect_encoding(path)
            self.assertIn(enc, ("cp1252", "latin-1"))
        finally:
            path.unlink()

    def test_strip_ansi(self):
        text = "\x1B[31mERROR\x1B[0m: something"
        self.assertEqual(strip_ansi(text), "ERROR: something")

    def test_read_text_lines_no_ansi_strip_for_py(self):
        """ANSI stripping should NOT run for .py files (optimization)."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write("line with \x1B[31mcolor\x1B[0m\n")
            path = Path(f.name)
        try:
            lines = list(read_text_lines(path))
            # .py is not in ANSI_EXTENSIONS, so escape codes should remain
            self.assertIn("\x1B[31m", lines[0])
        finally:
            path.unlink()

    def test_read_text_lines_strips_ansi_for_log(self):
        """ANSI stripping SHOULD run for .log files."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False, encoding="utf-8"
        ) as f:
            f.write("line with \x1B[31mcolor\x1B[0m\n")
            path = Path(f.name)
        try:
            lines = list(read_text_lines(path))
            self.assertNotIn("\x1B[31m", lines[0])
            self.assertIn("color", lines[0])
        finally:
            path.unlink()


# =========================================================================
# Filter Tests
# =========================================================================

class TestFilters(unittest.TestCase):
    def test_skip_dirs_includes_vcs(self):
        for d in (".git", ".hg", ".svn"):
            self.assertIn(d, SKIP_DIRS, f"{d} missing from SKIP_DIRS")

    def test_skip_dirs_includes_envs(self):
        for d in ("venv", ".venv", "node_modules"):
            self.assertIn(d, SKIP_DIRS, f"{d} missing from SKIP_DIRS")

    def test_useful_extensions_per_spec(self):
        for ext in (".py", ".pyw", ".js", ".ts", ".jsx", ".tsx", ".java",
                     ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".cs",
                     ".c", ".cpp", ".h", ".hpp",
                     ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
                     ".conf", ".xml",
                     ".md", ".markdown", ".rst", ".txt", ".adoc",
                     ".html", ".css", ".scss", ".sass"):
            self.assertIn(ext, USEFUL_EXTENSIONS, f"{ext} missing")

    def test_max_file_size_constant(self):
        self.assertEqual(MAX_FILE_SIZE_BYTES, 100 * 1024 * 1024)


# =========================================================================
# Writer Tests
# =========================================================================

class TestWriter(unittest.TestCase):
    def test_normalize_extension(self):
        self.assertEqual(normalize_extension(".py"), "py")
        self.assertEqual(normalize_extension(""), "no_extension")
        self.assertEqual(normalize_extension(".PY"), "py")

    def test_streaming_index_written(self):
        """Index should be streamed to disk, not held in memory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")

            output_dir = root / "scan_output"
            config = ScanConfig(
                root=root,
                output_dir=output_dir,
                error_file=output_dir / "error.log",
                mode="single",
                max_output_files=5,
                max_chunk_mb=10.0,
                dry_run=False,
                progress=False,
            )

            scanner = DirectoryScanner(config)
            scanner.scan()

            index_file = output_dir / "index.json"
            self.assertTrue(index_file.exists())
            data = json.loads(index_file.read_text(encoding="utf-8"))
            self.assertIsInstance(data, dict)
            self.assertIn("files", data)
            self.assertGreater(len(data["files"]), 0)


# =========================================================================
# Chunk Manager Tests
# =========================================================================

class TestChunkManager(unittest.TestCase):
    def test_should_not_rotate_when_empty(self):
        mgr = ChunkManager(safe_chunk_bytes=1000, max_output_files=5)
        self.assertFalse(mgr.should_rotate(500))

    def test_should_rotate_when_full(self):
        mgr = ChunkManager(safe_chunk_bytes=1000, max_output_files=5)
        mgr.record(".py", 800)
        self.assertTrue(mgr.should_rotate(300))

    def test_rotate_increments_part(self):
        mgr = ChunkManager(safe_chunk_bytes=1000, max_output_files=5)
        mgr.record(".py", 800)
        new_state = mgr.rotate()
        self.assertEqual(new_state.part_number, 2)

    def test_rotate_exceeds_limit(self):
        mgr = ChunkManager(safe_chunk_bytes=100, max_output_files=1)
        with self.assertRaises(RuntimeError):
            mgr.rotate()

    def test_summary(self):
        mgr = ChunkManager(safe_chunk_bytes=1000, max_output_files=5)
        mgr.record(".py", 100)
        mgr.record(".js", 200)
        s = mgr.summary()
        self.assertEqual(s["total_chunks"], 1)
        self.assertEqual(s["total_bytes"], 300)
        self.assertEqual(s["total_entries"], 2)


if __name__ == "__main__":
    unittest.main()
