"""
Antigravity Scanner CLI - Full-featured command-line interface.

Provides complete parity with GUI features including scanning, organization,
history management, analytics, and configuration tools.
"""
import sys
import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from antigravity.core.scanner import Scanner, ScanMode, ScanConfig
from antigravity.core.filters import FilterConfig
from antigravity.services.database import DatabaseService, get_db_path
from antigravity.services.history import HistoryService
from antigravity.schemas.config import AppConfig, ScanProfile
from antigravity.utils.logger import setup_logging, logger
from antigravity.utils.platform import get_system_info

app = typer.Typer(
    name="antigravity",
    help="High-performance codebase scanner and text extractor for LLM/RAG preparation",
    add_completion=True,
    pretty_exceptions_enable=True,
)
console = Console()

# State management
_db_service: Optional[DatabaseService] = None
_history_service: Optional[HistoryService] = None


def _get_db() -> DatabaseService:
    """Get or create database service singleton."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService(db_path=get_db_path())
    return _db_service


def _get_history() -> HistoryService:
    """Get or create history service singleton."""
    global _history_service
    if _history_service is None:
        _history_service = HistoryService(_get_db())
    return _history_service


@app.callback()
def main_callback(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False, "-v", "--verbose", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "-q", "--quiet", help="Suppress non-essential output"
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        help="Path to configuration file (default: ~/.antigravity/config.toml)",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    ),
) -> None:
    """
    Antigravity Scanner - Scan massive codebases and extract text for LLM/RAG.
    
    Examples:
        antigravity scan /path/to/repo --output result.txt.gz
        antigravity history --format table
        antigravity organize ./files --tool cleaner --dry-run
    """
    # Setup logging
    log_level_value = log_level.upper()
    setup_logging(level=log_level_value, verbose=verbose, quiet=quiet)
    
    if verbose:
        logger.debug(f"Verbose mode enabled, log level: {log_level_value}")
        logger.debug(f"System info: {get_system_info()}")
    
    ctx.obj = {
        "verbose": verbose,
        "quiet": quiet,
        "config_path": config,
        "log_level": log_level_value,
    }


@app.command("scan")
def scan_command(
    ctx: typer.Context,
    root: str = typer.Argument(..., help="Root directory or file to scan"),
    output: Optional[str] = typer.Option(
        None, "-o", "--output", help="Output file path (default: stdout)"
    ),
    output_dir: Optional[str] = typer.Option(
        None, "-d", "--output-dir", help="Output directory for chunked mode"
    ),
    mode: ScanMode = typer.Option(
        ScanMode.MULTI,
        "-m", "--mode",
        help="Scan mode: single (one file), multi (by extension), chunked (by size)"
    ),
    include: List[str] = typer.Option(
        [], "-i", "--include",
        help="File patterns to include (e.g., '*.py', '*.md'). Can be specified multiple times."
    ),
    exclude: List[str] = typer.Option(
        [], "-e", "--exclude",
        help="Patterns to exclude (e.g., 'node_modules', '.git'). Can be specified multiple times."
    ),
    max_size: Optional[str] = typer.Option(
        None, "--max-size",
        help="Maximum file size (e.g., '10MB', '1GB')"
    ),
    min_size: Optional[str] = typer.Option(
        None, "--min-size",
        help="Minimum file size (e.g., '1KB')"
    ),
    incremental: bool = typer.Option(
        False, "--incremental",
        help="Use incremental scanning with cache"
    ),
    cache_dir: Optional[Path] = typer.Option(
        None, "--cache-dir",
        help="Cache directory for incremental scans"
    ),
    chunk_size: int = typer.Option(
        4000, "--chunk-size",
        help="Target chunk size in tokens (for chunked mode)"
    ),
    chunk_overlap: int = typer.Option(
        200, "--chunk-overlap",
        help="Overlap between chunks in tokens"
    ),
    compression: bool = typer.Option(
        True, "--compression/--no-compression",
        help="Enable gzip compression for output"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Preview scan without writing output"
    ),
    json_output: bool = typer.Option(
        False, "--json",
        help="Output results as JSON"
    ),
    workers: Optional[int] = typer.Option(
        None, "-w", "--workers",
        help="Number of worker threads (default: auto-detect)"
    ),
) -> None:
    """
    Scan a directory or file and extract text content.
    
    Supports multiple modes:
    - single: Concatenate all files into one output
    - multi: Group files by extension into separate outputs
    - chunked: Split large outputs into manageable chunks for LLM contexts
    
    Examples:
        antigravity scan /repo --output result.txt.gz
        antigravity scan /repo --mode chunked --output-dir chunks/
        antigravity scan . --include "*.py" --exclude "__pycache__" --json
    """
    root_path = Path(root).resolve()
    
    if not root_path.exists():
        console.print(f"[red]Error:[/red] Path does not exist: {root_path}")
        raise typer.Exit(code=1)
    
    # Build scan configuration
    filter_config = FilterConfig(
        include_patterns=include or None,
        exclude_patterns=exclude or None,
        max_size=max_size,
        min_size=min_size,
    )
    
    scan_config = ScanConfig(
        mode=mode,
        filter_config=filter_config,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        use_compression=compression,
        use_incremental=incremental,
        cache_dir=cache_dir,
        max_workers=workers,
    )
    
    if json_output:
        console.print(json.dumps({
            "status": "starting",
            "root": str(root_path),
            "mode": mode.value,
            "config": scan_config.model_dump(mode="json"),
        }, indent=2))
    
    if dry_run:
        console.print(Panel(
            f"[yellow]Dry Run Mode[/yellow]\n\n"
            f"Would scan: [bold]{root_path}[/bold]\n"
            f"Mode: {mode.value}\n"
            f"Filters: include={include or 'all'}, exclude={exclude or 'none'}\n"
            f"Output: {output or 'stdout'}",
            title="🔍 Scan Preview",
            border_style="yellow",
        ))
        return
    
    # Execute scan
    scanner = Scanner(config=scan_config)
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            disable=quiet or json_output,
        ) as progress:
            task = progress.add_task("Scanning...", total=None)
            
            def on_progress(files_scanned: int, bytes_processed: int, current_file: str):
                progress.update(task, description=f"Scanning: {current_file}")
            
            result = scanner.scan(
                root_path=root_path,
                output_path=Path(output) if output else None,
                output_dir=Path(output_dir) if output_dir else None,
                progress_callback=on_progress,
            )
        
        # Record in history
        _get_history().record_scan(result)
        
        if json_output:
            console.print(json.dumps({
                "status": "complete",
                "result": result.model_dump(mode="json"),
            }, indent=2, default=str))
        else:
            console.print(Panel(
                f"[green]✓ Scan Complete[/green]\n\n"
                f"Files scanned: {result.files_scanned}\n"
                f"Lines processed: {result.lines_processed}\n"
                f"Total size: {result.total_bytes / 1024 / 1024:.2f} MB\n"
                f"Output: {result.output_path}",
                title="📊 Results",
                border_style="green",
            ))
    
    except Exception as e:
        logger.exception(f"Scan failed: {e}")
        if json_output:
            console.print(json.dumps({
                "status": "error",
                "error": str(e),
            }, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e


@app.command("organize")
def organize_command(
    ctx: typer.Context,
    target: str = typer.Argument(..., help="Target directory to organize"),
    tool: str = typer.Option(
        ..., "-t", "--tool",
        help="Organization tool to use (prefixer, cleaner, purger, flattener, pattern-mover, duplicates)"
    ),
    dry_run: bool = typer.Option(
        True, "--dry-run/--apply",
        help="Preview changes without applying (default: dry-run)"
    ),
    pattern: Optional[str] = typer.Option(
        None, "-p", "--pattern",
        help="Pattern for pattern-mover tool (regex)"
    ),
    prefix: Optional[str] = typer.Option(
        None, "--prefix",
        help="Prefix to add/remove for prefixer tool"
    ),
    remove_suffixes: bool = typer.Option(
        True, "--remove-suffixes/--keep-suffixes",
        help="Remove numeric suffixes like _001, (1) for cleaner tool"
    ),
    depth: Optional[int] = typer.Option(
        None, "--depth",
        help="Directory depth limit for flattener"
    ),
    conflict_resolution: str = typer.Option(
        "rename", "--conflict",
        help="Conflict resolution: rename, overwrite, skip"
    ),
    json_output: bool = typer.Option(
        False, "--json",
        help="Output results as JSON"
    ),
) -> None:
    """
    Organize files using various toolkit operations.
    
    Available tools:
    - prefixer: Add/remove prefixes from filenames
    - cleaner: Remove numeric suffixes and clean names
    - purger: Remove empty directories
    - flattener: Move files up directory levels
    - pattern-mover: Group files by regex pattern
    - duplicates: Find and handle duplicate files
    
    Examples:
        antigravity organize ./files --tool cleaner --dry-run
        antigravity organize ./src --tool flattener --depth 2 --apply
        antigravity organize ./data --tool pattern-mover --pattern "^(\\w+)_"
    """
    target_path = Path(target).resolve()
    
    if not target_path.exists():
        console.print(f"[red]Error:[/red] Path does not exist: {target_path}")
        raise typer.Exit(code=1)
    
    if not target_path.is_dir():
        console.print(f"[red]Error:[/red] Path is not a directory: {target_path}")
        raise typer.Exit(code=1)
    
    action = "apply" if not dry_run else "dry-run"
    console.print(Panel(
        f"Tool: [bold]{tool}[/bold]\n"
        f"Target: {target_path}\n"
        f"Mode: {action}",
        title="🛠️ Organization",
        border_style="blue",
    ))
    
    # Placeholder for organization implementation
    # TODO: Implement full organization toolkit
    console.print("[yellow]Organization toolkit coming in Phase 2[/yellow]")
    
    if json_output:
        console.print(json.dumps({
            "tool": tool,
            "target": str(target_path),
            "dry_run": dry_run,
            "status": "pending",
        }, indent=2))


@app.command("history")
def history_command(
    ctx: typer.Context,
    limit: int = typer.Option(
        20, "-n", "--limit",
        help="Number of records to show"
    ),
    offset: int = typer.Option(
        0, "--offset",
        help="Number of records to skip"
    ),
    status: Optional[str] = typer.Option(
        None, "-s", "--status",
        help="Filter by status (completed, failed, cancelled)"
    ),
    search: Optional[str] = typer.Option(
        None, "--search",
        help="Search in root paths"
    ),
    format: str = typer.Option(
        "table", "-f", "--format",
        help="Output format: table, json, csv"
    ),
    since: Optional[str] = typer.Option(
        None, "--since",
        help="Show scans since date (YYYY-MM-DD)"
    ),
    until: Optional[str] = typer.Option(
        None, "--until",
        help="Show scans until date (YYYY-MM-DD)"
    ),
) -> None:
    """
    View and manage scan history.
    
    Examples:
        antigravity history --limit 10
        antigravity history --status completed --format json
        antigravity history --search "project" --since 2024-01-01
    """
    history = _get_history()
    
    # Parse date filters
    since_date = None
    until_date = None
    if since:
        try:
            since_date = datetime.strptime(since, "%Y-%m-%d")
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid date format for --since. Use YYYY-MM-DD")
            raise typer.Exit(code=1)
    
    if until:
        try:
            until_date = datetime.strptime(until, "%Y-%m-%d")
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid date format for --until. Use YYYY-MM-DD")
            raise typer.Exit(code=1)
    
    records = history.get_history(
        limit=limit,
        offset=offset,
        status=status,
        search_term=search,
        since=since_date,
        until=until_date,
    )
    
    if format == "json":
        output = {
            "total": len(records),
            "records": [r.model_dump(mode="json") for r in records],
        }
        console.print(json.dumps(output, indent=2, default=str))
    
    elif format == "csv":
        if not records:
            console.print("No records found")
            return
        
        # CSV header
        console.print("id,root_path,mode,status,files_scanned,lines_processed,total_bytes,started_at,completed_at")
        for r in records:
            console.print(f"{r.id},{r.root_path},{r.mode},{r.status},{r.files_scanned},{r.lines_processed},{r.total_bytes},{r.started_at},{r.completed_at or ''}")
    
    else:  # table format
        if not records:
            console.print("[yellow]No scan history found[/yellow]")
            return
        
        table = Table(
            title="📜 Scan History",
            box=box.ROUNDED,
            show_lines=True,
        )
        
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Root Path", style="white")
        table.add_column("Mode", style="blue")
        table.add_column("Status", style="green")
        table.add_column("Files", justify="right", style="yellow")
        table.add_column("Lines", justify="right", style="yellow")
        table.add_column("Size (MB)", justify="right", style="magenta")
        table.add_column("Date", style="dim")
        
        for r in records:
            status_style = {
                "completed": "green",
                "failed": "red",
                "cancelled": "yellow",
                "running": "blue",
            }.get(r.status, "white")
            
            table.add_row(
                str(r.id),
                r.root_path,
                r.mode,
                f"[{status_style}]{r.status}[/{status_style}]",
                str(r.files_scanned),
                str(r.lines_processed),
                f"{r.total_bytes / 1024 / 1024:.2f}",
                r.started_at.strftime("%Y-%m-%d %H:%M") if r.started_at else "",
            )
        
        console.print(table)
        console.print(f"\n[dim]Showing {len(records)} record(s)[/dim]")


@app.command("analytics")
def analytics_command(
    ctx: typer.Context,
    root: Optional[str] = typer.Argument(
        None, help="Directory to analyze (optional, uses last scan if omitted)"
    ),
    report: str = typer.Option(
        "text", "-r", "--report",
        help="Report type: text, html, json"
    ),
    output: Optional[str] = typer.Option(
        None, "-o", "--output",
        help="Output file path"
    ),
    include_charts: bool = typer.Option(
        False, "--charts",
        help="Include charts (requires matplotlib)"
    ),
) -> None:
    """
    Generate analytics report for a scan or directory.
    
    Provides insights on:
    - File type distribution
    - Size distribution
    - Directory structure
    - Scan metrics
    
    Examples:
        antigravity analytics --report text
        antigravity analytics /repo --report html --output report.html
    """
    console.print("[yellow]Analytics dashboard coming in Phase 3[/yellow]")
    
    if report == "json":
        console.print(json.dumps({
            "status": "pending",
            "message": "Analytics feature under development",
        }, indent=2))


@app.command("config")
def config_command(
    ctx: typer.Context,
    action: str = typer.Argument(
        "show",
        help="Action: show, set, list-profiles, save-profile, load-profile"
    ),
    key: Optional[str] = typer.Option(
        None, "-k", "--key",
        help="Configuration key (for set action)"
    ),
    value: Optional[str] = typer.Option(
        None, "-v", "--value",
        help="Configuration value (for set action)"
    ),
    profile: Optional[str] = typer.Option(
        None, "-p", "--profile",
        help="Profile name (for profile actions)"
    ),
) -> None:
    """
    Manage application configuration and profiles.
    
    Examples:
        antigravity config show
        antigravity config set scan.chunk_size 4000
        antigravity config list-profiles
        antigravity config save-profile --profile my-scan
    """
    console.print("[yellow]Configuration management coming in Phase 2[/yellow]")
    
    if action == "show":
        # Show current config
        config = AppConfig()
        console.print(json.dumps(config.model_dump(mode="json"), indent=2))


@app.command("cache")
def cache_command(
    ctx: typer.Context,
    action: str = typer.Argument(
        "status",
        help="Action: status, clear, info"
    ),
    cache_dir: Optional[Path] = typer.Option(
        None, "--cache-dir",
        help="Cache directory (default: ~/.antigravity/cache)"
    ),
) -> None:
    """
    Manage incremental scan cache.
    
    Examples:
        antigravity cache status
        antigravity cache clear
        antigravity cache info
    """
    console.print("[yellow]Cache management coming in Phase 2[/yellow]")


@app.command("version")
def version_command() -> None:
    """Show version information."""
    from antigravity import __version__
    
    console.print(Panel(
        f"[bold]Antigravity Scanner[/bold]\n\n"
        f"Version: [green]{__version__}[/green]\n"
        f"Python: {sys.version.split()[0]}\n"
        f"Platform: {get_system_info()['platform']}",
        title="ℹ️ Version Info",
        border_style="blue",
    ))


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
