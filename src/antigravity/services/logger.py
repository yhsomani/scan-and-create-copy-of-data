"""
Centralized logging system for the application.
Provides file rotation and a custom Qt signal handler for UI redirection.
"""
import logging
import logging.handlers
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

class QtLogSignals(QObject):
    log_emitted = pyqtSignal(str)

class QtLogHandler(logging.Handler):
    """Logging handler that emits a Qt signal for UI console updates."""
    def __init__(self, signals: QtLogSignals):
        super().__init__()
        self.signals = signals

    def emit(self, record):
        msg = self.format(record)
        self.signals.log_emitted.emit(msg)

def setup_logging(log_file: str = "scanner.log") -> QtLogSignals:
    """Initialize logging with file and console outputs."""
    log_dir = Path.cwd() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    signals = QtLogSignals()
    
    # Root logger
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File Handler (Rotating)
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / log_file, maxBytes=5*1024*1024, backupCount=3
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # UI Handler
    ui_handler = QtLogHandler(signals)
    ui_handler.setFormatter(formatter)
    logger.addHandler(ui_handler)
    
    # Standard Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return signals
