import logging
import traceback
from pathlib import Path
from typing import Optional, Callable
from PyQt6.QtCore import QObject, pyqtSlot, QRunnable, QThreadPool, pyqtSignal
from antigravity.core.scanner import DirectoryScanner
from antigravity.services.config import ScanConfig
from antigravity.services.history import ScanHistoryService
from antigravity.services.settings import SettingsService
from antigravity.services.logger import QtLogSignals
from antigravity.tools.file_organizer_toolkit import (
    prefix_files_with_folder, 
    remove_folder_prefixes, 
    organize_into_folders,
    flatten_directory_to_root,
    purge_empty_directories,
    run_system_cleanup,
    deduplicate_files,
    rename_to_hash
)

# ── Async Workers ─────────────────────────────────────────────────────────────

class WorkerSignals(QObject):
    """Signals for background workers."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)

class ScanWorker(QRunnable):
    """Background worker for the directory scanner."""
    def __init__(self, config: ScanConfig):
        super().__init__()
        self.config = config
        self.signals = WorkerSignals()
        self.scanner: Optional[DirectoryScanner] = None

    @pyqtSlot()
    def run(self):
        try:
            self.scanner = DirectoryScanner(self.config)
            metrics = self.scanner.scan()
            self.signals.finished.emit(metrics.summary())
        except Exception as e:
            self.signals.error.emit(str(e))
            logging.error(traceback.format_exc())

class ToolWorker(QRunnable):
    """Background worker for toolkit operations."""
    def __init__(self, func: Callable, path: Path):
        super().__init__()
        self.func = func
        self.path = path
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            ops = self.func(self.path)
            self.signals.finished.emit(ops)
        except Exception as e:
            self.signals.error.emit(str(e))

# ── Main Controller ───────────────────────────────────────────────────────────

class AppController(QObject):
    """Bridges the GUI with the Core and Services."""
    def __init__(self, shell):
        super().__init__()
        self.shell = shell
        self.history_svc = ScanHistoryService()
        self.settings_svc = SettingsService()
        self.thread_pool = QThreadPool.globalInstance()
        
        # Setup logging redirection
        self.setup_logging()
        self.setup_connections()
        self.load_initial_data()

    def setup_logging(self):
        """Redirect engine logs to the UI console."""
        from antigravity.services.logger import setup_logging as init_logs
        self.log_signals = init_logs()
        self.log_signals.log_emitted.connect(self._on_log_received)

    def setup_connections(self):
        # Scanner connections
        self.shell.view_scanner.start_requested.connect(self.run_scan)
        
        # Toolkit connections
        self.shell.view_toolkit.tool_requested.connect(self.run_tool)
        
        # Settings connections
        self.shell.view_settings.save_requested.connect(self.save_settings)

    def load_initial_data(self):
        # Load history
        records = self.history_svc.get_all(limit=20)
        formatted = []
        for r in records:
            formatted.append({
                "date": r["created_at"].strftime("%Y-%m-%d %H:%M"),
                "name": Path(r["root_path"]).name,
                "mode": r["mode"],
                "size": f"{r['bytes'] / (1024*1024):.1f} MB",
                "id": r["id"]
            })
        self.shell.view_history.set_records(formatted)
        
        # Load settings
        self.settings_svc.bootstrap()
        settings = self.settings_svc.get_all()
        self.shell.view_settings.set_settings(settings)
        
        # Apply default workers to scanner view if set
        try:
            default_workers = int(settings.get("default_workers", "4"))
        except ValueError:
            default_workers = 4
        # Just keeping it loaded.

    @pyqtSlot(dict)
    def save_settings(self, settings: dict):
        self.settings_svc.set_many(settings)
        print("Settings saved successfully.")

    @pyqtSlot(str)
    def _on_log_received(self, msg: str):
        # We'll need to add a console/log view to the shell or a specific view
        # For now, let's assume views can handle logs if they want
        if hasattr(self.shell, "append_log"):
            self.shell.append_log(msg)

    @pyqtSlot(dict)
    def run_scan(self, config_dict: dict):
        try:
            if not config_dict.get("root") or not config_dict["root"].strip():
                print("Error: Target Directory cannot be empty.")
                if hasattr(self.shell, "append_log"):
                    self.shell.append_log("Error: Target Directory cannot be empty.")
                return

            config = ScanConfig(
                root=Path(config_dict["root"]).resolve(),
                output_dir=Path(config_dict["output_dir"]).resolve() if config_dict.get("output_dir") else None,
                mode="single",
                compress=config_dict["compress"],
                skip_hidden=config_dict["skip_hidden"],
                follow_links=config_dict["follow_links"],
                dry_run=config_dict["dry_run"],
                search_patterns=config_dict.get("search_patterns", []),
                progress=True
            )
            
            # Create history record
            record_id = self.history_svc.create_record(
                root_path=str(config.root),
                output_path=str(config.output_dir or ""),
                mode=config.mode
            )
            
            worker = ScanWorker(config)
            worker.signals.finished.connect(lambda s: self._on_scan_finished(record_id, s))
            worker.signals.error.connect(lambda e: print(f"Scan Error: {e}"))
            
            self.thread_pool.start(worker)
            self.shell.view_scanner.pulse.show()
            self.shell.view_scanner.scan_btn.setText("STOP ENGINE") # Placeholder for stop logic
            print("Engine started in background...")
            
        except Exception as e:
            print(f"Scan initiation failed: {e}")

    def _on_scan_finished(self, record_id, summary):
        self.history_svc.complete_record(record_id, summary)
        self.shell.view_scanner.update_metrics(summary)
        self.shell.view_scanner.pulse.hide()
        self.shell.view_scanner.scan_btn.setText("INITIATE SCAN SEQUENCE")
        self.load_initial_data()
        print("Scan sequence completed.")

    @pyqtSlot(str, str)
    def run_tool(self, tool_id: str, target_path: str):
        if not target_path:
            return
        
        p = Path(target_path).resolve()
        if not p.exists():
            return

        tool_map = {
            "prefix_add": prefix_files_with_folder,
            "prefix_remove": remove_folder_prefixes,
            "organize_iter": organize_into_folders,
            "flatten_root": flatten_directory_to_root,
            "purge_empty": purge_empty_directories,
            "deduplicate_files": deduplicate_files,
            "rename_to_hash": rename_to_hash,
            "sys_cleanup": run_system_cleanup
        }
        
        func = tool_map.get(tool_id)
        if not func: return
        
        worker = ToolWorker(func, p)
        worker.signals.finished.connect(lambda o: print(f"Tool {tool_id} finished. Ops: {o}"))
        worker.signals.error.connect(lambda e: print(f"Tool Error: {e}"))
        
        self.thread_pool.start(worker)
