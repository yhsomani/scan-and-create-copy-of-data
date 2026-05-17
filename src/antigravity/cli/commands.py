import logging
import sys
from pathlib import Path
from typing import Optional

import typer

from antigravity.services.config import ScanConfig
from antigravity.core.scanner import DirectoryScanner
from antigravity.utils.file_utils import load_ignore_patterns
from antigravity.cli.prompts import (
    prompt_for_root,
    prompt_for_output_dir,
    prompt_for_mode,
    prompt_for_format,
    prompt_for_max_output_files,
    prompt_for_max_chunk_mb,
    prompt_for_config_mode,
    prompt_for_ignore_file,
    prompt_for_cleanup,
)

logger = logging.getLogger("scan")
app = typer.Typer(add_completion=False, help="Directory scanner and code extractor")


def setup_logging(verbose: bool = False, log_file: Optional[Path] = None) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    format_str = "%(asctime)s [%(levelname)s] %(message)s"
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(log_file))
        except Exception:
            pass
    logging.basicConfig(level=level, format=format_str, handlers=handlers)
    logger.setLevel(level)


@app.command()
def run(
    root: Optional[str] = typer.Option(None, "--root", "-r", help="Root directory to scan"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir", "-o", help="Directory where outputs are written"),
    mode: str = typer.Option("single", "--mode", "-m", help="Output mode (single, multi, chunked)"),

    max_output_files: int = typer.Option(5, "--max-output-files", help="Maximum output files"),
    max_chunk_mb: float = typer.Option(10.0, "--max-chunk-mb", help="Maximum size for each output chunk in MB"),
    config_mode: Optional[str] = typer.Option(None, "--config-mode", help="1 = manual, 2 = auto-calc"),
    auto_calc: bool = typer.Option(False, "--auto-calc", help="Estimate total bytes and compute required output files"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run without writing output files"),
    resume: bool = typer.Option(False, "--resume", help="Resume interrupted scan"),
    progress: bool = typer.Option(True, "--progress/--no-progress", help="Enable progress tracking"),
    ignore_file: str = typer.Option(".scanignore", "--ignore-file", help="Name of ignore file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    follow_links: bool = typer.Option(False, "--follow-links", help="Follow symbolic links"),
    include_hidden: bool = typer.Option(False, "--include-hidden", help="Include hidden files"),
    allow_large_files: bool = typer.Option(True, "--allow-large-files", help="Allow large files"),
    cleanup: bool = typer.Option(False, "--cleanup", help="Delete output files after scan"),
    simple_output: bool = typer.Option(False, "--simple-output", help="Use simple progress output"),
    config_file: Optional[str] = typer.Option(None, "--config", help="Path to config file"),
    compress: bool = typer.Option(False, "--compress", help="Compress output files"),
    log_file: Optional[str] = typer.Option(None, "--log-file", help="Path to log file"),
    workers: int = typer.Option(1, "--workers", help="Number of parallel workers"),

    incremental: bool = typer.Option(False, "--incremental", help="Skip unmodified files"),
):
    try:
        if config_file:
            path = Path(config_file)
            config = ScanConfig.load_config(path, base_path=path.parent)
            setup_logging(config.verbose, config.log_file)
            logger.info(f"Loaded config from {config_file}")
            auto_calc = False
        else:
            if not root:
                # Interactive mode
                root_path = prompt_for_root()
                output_path = prompt_for_output_dir(root_path)
                mode = prompt_for_mode()
                format = prompt_for_format()
                config_mode_choice = prompt_for_config_mode()
                if config_mode_choice == "2":
                    auto_calc = True
                max_chunk_mb = prompt_for_max_chunk_mb()
                max_output_files = prompt_for_max_output_files()
                ignore_file = prompt_for_ignore_file()
            else:
                root_path = Path(root).expanduser().resolve()
                output_path = Path(output_dir).expanduser().resolve() if output_dir else root_path / "scan_output"

            ignore_patterns = load_ignore_patterns(root_path, ignore_file)
            
            config = ScanConfig(
                root=root_path,
                output_dir=output_path,
                mode=mode,
                max_output_files=max_output_files or 5,
                max_chunk_mb=max_chunk_mb or 10.0,
                dry_run=dry_run,
                resume=resume,
                progress=progress,
                verbose=verbose,
                ignore_file_name=ignore_file,
                ignore_patterns=ignore_patterns,
                follow_links=follow_links,
                skip_hidden=not include_hidden,
                allow_large_files=allow_large_files,
                simple_output=simple_output,
                compress=compress,
                log_file_name=str(log_file) if log_file else "scan.log",
                workers=workers,

                incremental=incremental,
                auto_calc=auto_calc,
            )
            setup_logging(config.verbose, config.log_file)

        logger.info(f"Starting scan of {config.root}")
        logger.info(f"Mode: {config.mode}, Output: {config.output_dir}")

        scanner = DirectoryScanner(config)

        metrics = scanner.scan()
        logger.info("Scan complete.")

        print("\n" + "=" * 50)
        print("SCAN SUMMARY")
        print("=" * 50)
        summary = metrics.summary()
        print(f"Files processed: {summary['files_processed']}")
        print(f"Files skipped: {summary['files_skipped']}")
        print(f"Lines of code: {summary['lines_processed']}")
        print(f"Bytes processed: {summary['bytes_processed']}")
        print(f"Elapsed: {summary['elapsed_seconds']}s")

        print(f"\nOutput directory: {config.output_dir}")

        if not root and not cleanup:
            cleanup = prompt_for_cleanup()

        if cleanup:
            import shutil
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
            for h in logging.root.handlers[:]:
                h.close()
                logging.root.removeHandler(h)
            
            logger.info("Cleaning up output files...")
            try:
                if config.output_dir and config.output_dir.exists():
                    shutil.rmtree(config.output_dir)
                    print(f"Removed directory: {config.output_dir}")
            except Exception as e:
                print(f"Could not remove: {e}")
            raise typer.Exit(0)

    except KeyboardInterrupt:
        logger.warning("Scan interrupted by user")
        try:
            if "scanner" in locals() and scanner is not None:
                scanner.writer.finalize()
                if config.resume:
                    scanner.save_state(getattr(scanner, "_last_relative_path", ""))
        except Exception:
            pass
        raise typer.Exit(130)
    except Exception as exc:
        logger.error(f"Fatal error: {exc}")
        raise typer.Exit(1)


def main(argv=None):
    # This acts as the bridge for older tests and entrypoints calling main()
    # Note: Typer natively handles sys.argv, so passing argv directly to app() works if modified
    import sys
    if argv is not None:
        sys.argv = [sys.argv[0]] + argv
    app()


if __name__ == "__main__":
    app()
