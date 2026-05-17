import typer
from rich.console import Console
from antigravity.utils.logger import logger

app = typer.Typer(
    name="antigravity",
    help="Antigravity Scanner — High-performance directory analysis.",
    add_completion=False,
)
console = Console()

@app.command()
def scan(
    root: str = typer.Argument(..., help="Root directory to scan"),
    output: str = typer.Option("./output", "-o", "--output", help="Output directory"),
    mode: str = typer.Option("single", help="Output mode: single, multi, chunked"),
) -> None:
    """Run the directory scanning engine."""
    logger.info(f"Starting scan on {root} -> {output} in {mode} mode.")
    # Implementation for phase 1

@app.command()
def organize(
    target: str = typer.Argument(..., help="Target directory to organize"),
) -> None:
    """Run the organization toolkit."""
    logger.info(f"Starting organization on {target}.")
    # Implementation for phase 1

if __name__ == "__main__":
    app()
