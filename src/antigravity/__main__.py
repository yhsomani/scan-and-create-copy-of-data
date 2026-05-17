import sys
from pathlib import Path

# Ensure 'src' is in sys.path so we can import 'antigravity' when running directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from antigravity.cli import app
from antigravity.utils.logger import logger

def main() -> None:
    # If no arguments are provided, default to GUI
    if len(sys.argv) == 1:
        try:
            from antigravity.gui.app import main as launch_gui
            launch_gui()
        except ImportError as e:
            logger.error(f"Failed to load GUI: {e}")
            logger.info("Running in CLI mode instead. Use --help for options.")
            app(["--help"])
    else:
        app()

if __name__ == "__main__":
    main()
