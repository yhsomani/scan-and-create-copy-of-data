"""
Scanner Configuration view — Primary tab, Advanced tab, Rules tab.
Full feature parity with ScanConfig backend.
"""
from __future__ import annotations

import sys
from pathlib import Path
from queue import Queue
from typing import Callable, Optional

from PyQt6.QtCore import QObject, QRunnable, QThread, QThreadPool, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox, QFileDialog, QFrame, QGroupBox, QHBoxLayout,
    QLabel, QPlainTextEdit, QPushButton, QSizePolicy,
    QSplitter, QTabWidget, QVBoxLayout, QWidget, QScrollArea
)

from antigravity.gui.components import (
    M3Button, M3Dropdown, M3Input, ProgressRow,
    SectionHeader, Separator, StatCard, PulseIndicator
)
from antigravity.services.history import ScanHistoryService
from antigravity.services.settings import SettingsService
from antigravity.gui.theme import TOKENS
from antigravity.services.config import ScanConfig


# ─────────────────────────── Worker Signals ──────────────────────────────── #

class ScanSignals(QObject):
    log = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)


class ScanWorker(QRunnable):
    """Runs the scanner in a thread pool slot."""

    def __init__(self, config: ScanConfig, record_id: Optional[int], signals: ScanSignals, parent_view=None) -> None:
        super().__init__()
        self._config = config
        self._record_id = record_id
        self.signals = signals
        self._parent_view = parent_view
        self.setAutoDelete(True)

    @pyqtSlot()
    def run(self) -> None:
        import logging
        import traceback
        logger = logging.getLogger("ScanEngine")
        
        try:
            from antigravity.core.scanner import DirectoryScanner
            from antigravity.services.config import ScanConfig
            scanner = DirectoryScanner(self._config)
            
            # Register scanner instance for cancellation
            if self._parent_view:
                self._parent_view._current_scanner = scanner
            
            logger.info(f"Starting scan for {self._config.root}...")
            metrics = scanner.scan()
            
            self.signals.finished.emit(metrics.summary())
            logger.info("Scan completed successfully.")

        except Exception as exc:
            err_msg = f"INTERNAL_SCAN_FAILURE: {str(exc)}"
            logger.error(err_msg)
            logger.error(traceback.format_exc())
            self.signals.error.emit(err_msg)


class ToolWorker(QRunnable):
    """Runs organization tools in the background."""
    def __init__(self, func, path, callback, snackbar_signal):
        super().__init__()
        self.func = func
        self.path = path
        self.callback = callback
        self.snackbar_signal = snackbar_signal
        self.setAutoDelete(True)

    @pyqtSlot()
    def run(self):
        try:
            count = self.func(self.path)
            self.callback(count)
        except Exception as e:
            self.snackbar_signal.emit(str(e), "error")


# ─────────────────────────── Config View ─────────────────────────────────── #

class ScanConfigView(QWidget):
    scan_completed = pyqtSignal(dict)   # emits summary dict
    scan_started = pyqtSignal()
    snackbar_request = pyqtSignal(str, str)  # message, kind

    def __init__(
        self,
        settings: SettingsService,
        history_svc: ScanHistoryService,
        log_signals=None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._history_svc = history_svc
        self._log_signals = log_signals
        
        if self._log_signals:
            self._log_signals.log_emitted.connect(self._on_log)

        self._current_record_id: Optional[int] = None
        self._current_scanner = None
        self._pool = QThreadPool.globalInstance()

        self._build_ui()
        self._load_defaults()

    # ── UI Construction ───────────────────────────────────────────────────── #

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(24)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 12)
        
        title_stack = QVBoxLayout()
        title_stack.setSpacing(0)
        self._main_title = QLabel("Antigravity Scanner")
        self._main_title.setStyleSheet(f"color: {TOKENS['on_background']}; font-size: 24px; font-weight: bold;")
        title_stack.addWidget(self._main_title)
        
        self._status_line = QHBoxLayout()
        self._status_line.setSpacing(8)
        self._pulse = PulseIndicator()
        self._pulse.hide()
        self._status_line.addWidget(self._pulse)
        
        self._status_label = QLabel("SYSTEM_STABLE")
        self._status_label.setStyleSheet(f"color: {TOKENS['on_surface_secondary']}; font-size: 10px; font-weight: bold;")
        self._status_line.addWidget(self._status_label)
        self._status_line.addStretch()
        title_stack.addLayout(self._status_line)
        
        header.addLayout(title_stack)
        header.addStretch()
        
        self._open_btn = M3Button("OPEN_OUTPUT", variant="outlined")
        self._open_btn.clicked.connect(self._open_output)
        header.addWidget(self._open_btn)
        
        root.addLayout(header)

        # ── Splitter: config (left) | console (right) ── #
        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)

        # Left: settings tabs
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_primary_tab(), "Primary")
        self._tabs.addTab(self._build_advanced_tab(), "Advanced")
        self._tabs.addTab(self._build_org_tab(), "Organization")
        left_layout.addWidget(self._tabs)

        # Stat Row
        self._stat_files  = StatCard("Files",  "—")
        self._stat_bytes  = StatCard("Size",   "—")
        self._stat_time   = StatCard("Time",   "—")

        stat_row = QHBoxLayout()
        for card in [self._stat_files, self._stat_bytes, self._stat_time]:
            stat_row.addWidget(card)
        left_layout.addLayout(stat_row)

        # CTA
        self._scan_btn = QPushButton("START ENGINE")
        self._scan_btn.setMinimumHeight(56)
        self._scan_btn.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self._scan_btn.clicked.connect(self._start_scan)
        left_layout.addWidget(self._scan_btn)

        self._progress = ProgressRow()
        left_layout.addWidget(self._progress)

        splitter.addWidget(left)

        # Right: console
        right = QFrame()
        right.setProperty("class", "card")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        console_header = QFrame()
        console_header.setFixedHeight(44)
        console_header.setStyleSheet("background: #2B2930; border-radius: 16px 16px 0 0;")
        ch_layout = QHBoxLayout(console_header)
        ch_layout.setContentsMargins(16, 0, 16, 0)
        con_title = QLabel("Engine Log")
        con_title.setProperty("class", "label_primary")
        ch_layout.addWidget(con_title)
        ch_layout.addStretch()
        
        self._console = QPlainTextEdit()
        self._console.setReadOnly(True)
        
        from antigravity.gui.components import CopyButton
        copy_btn = CopyButton(self._console)
        ch_layout.addWidget(copy_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedSize(60, 28)
        clear_btn.setProperty("class", "outlined")
        clear_btn.clicked.connect(self._clear_console)
        ch_layout.addWidget(clear_btn)
        right_layout.addWidget(console_header)
        self._console.setFont(QFont("Consolas", 12))
        self._console.setStyleSheet(
            f"background: {TOKENS['surface_1']}; color: {TOKENS['on_background']}; border: none; border-radius: 0 0 16px 16px; padding: 12px;"
        )
        self._console.document().setMaximumBlockCount(2000)
        right_layout.addWidget(self._console)

        splitter.addWidget(right)
        
        splitter.setSizes([620, 420])
        root.addWidget(splitter)

    def _build_primary_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        self._target_input = M3Input(
            "Target Directory",
            browse=True,
            browse_callback=self._browse_target,
        )
        self._target_input.setToolTip("The root directory to analyze. All code and assets within will be ingested.")
        
        self._output_input = M3Input(
            "Output Location",
            browse=True,
            browse_callback=self._browse_output,
        )
        self._output_input.setToolTip("Where the generated scan results and indices will be stored.")
        
        layout.addWidget(self._target_input)
        layout.addWidget(self._output_input)

        row = QHBoxLayout()
        row.setSpacing(16)
        self._mode_dd = M3Dropdown("Scan Mode", ["single", "multi", "chunked"], "single")
        self._workers = M3Dropdown("Parallel Workers", ["1", "2", "4", "8", "16"], "4")
        row.addWidget(self._mode_dd)
        row.addWidget(self._workers)
        layout.addLayout(row)

        layout.addSpacing(16)
        
        # Recent Scans Section
        self._recent_box = QGroupBox("Recent Scans")
        rb_layout = QVBoxLayout(self._recent_box)
        rb_layout.setSpacing(8)
        self._recent_list = QVBoxLayout()
        rb_layout.addLayout(self._recent_list)
        layout.addWidget(self._recent_box)
        
        self._refresh_recent()

        layout.addStretch()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(w)
        return scroll

    def _build_advanced_tab(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Chunking
        chunk_box = QGroupBox("Chunking & Limits")
        cb_layout = QVBoxLayout(chunk_box)
        cb_layout.setSpacing(12)
        from PyQt6.QtWidgets import QSpinBox, QDoubleSpinBox
        self._max_files  = self._labeled_spin("Max Output Files", 1, 100, 5)
        self._max_mb     = self._labeled_dspin("Max Chunk Size (MB)", 1.0, 500.0, 10.0)
        cb_layout.addWidget(self._max_files[0])
        cb_layout.addWidget(self._max_mb[0])
        cb_layout.addStretch()

        # Engine flags
        flag_box = QGroupBox("Engine Behaviors")
        fb_layout = QVBoxLayout(flag_box)
        fb_layout.setSpacing(10)
        self._resume_cb      = self._switch("Resume previous scan")
        self._incremental_cb = self._switch("Incremental caching")
        self._links_cb       = self._switch("Follow symlinks")
        self._compress_cb    = self._switch("Gzip compression (.gz)")
        self._dry_run_cb     = self._switch("Dry run (no write)")
        self._verbose_cb     = self._switch("Verbose logging")
        self._cleanup_cb     = self._switch("Delete output directory before scan")
        self._auto_calc_cb   = self._switch("Auto-calculate output partitions")
        for w2 in [self._resume_cb, self._incremental_cb, self._links_cb,
                   self._compress_cb, self._dry_run_cb, self._verbose_cb, 
                   self._cleanup_cb, self._auto_calc_cb]:
            fb_layout.addWidget(w2)
        fb_layout.addStretch()

        layout.addWidget(chunk_box)
        layout.addWidget(flag_box)

        # File Filters (Merged from Rules)
        filter_box = QGroupBox("File Filters & Ignore")
        fb_layout = QVBoxLayout(filter_box)
        fb_layout.setSpacing(10)
        self._skip_hidden_cb  = self._switch("Skip hidden files & directories")
        self._large_files_cb  = self._switch("Allow large file processing")
        self._ignore_file_input = M3Input("Ignore File Name", placeholder=".scanignore")
        fb_layout.addWidget(self._skip_hidden_cb)
        fb_layout.addWidget(self._large_files_cb)
        fb_layout.addWidget(self._ignore_file_input)
        layout.addWidget(filter_box)
        
        layout.addStretch()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(w)
        return scroll

    def _build_org_tab(self) -> QWidget:
        """New tab for file organization tools integrated from Python scripts."""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QLabel("UNIVERSAL_FILE_ORGANIZER")
        header.setStyleSheet(f"color: {TOKENS['primary']}; font-weight: bold; font-size: 14px;")
        layout.addWidget(header)

        # Prefix Management
        prefix_box = QGroupBox("Prefix Management")
        p_layout = QHBoxLayout(prefix_box)
        self._add_prefix_btn = M3Button("Add Folder Prefix", variant="outlined")
        self._add_prefix_btn.clicked.connect(self._run_add_prefix)
        self._rem_prefix_btn = M3Button("Remove Prefix", variant="outlined")
        self._rem_prefix_btn.clicked.connect(self._run_rem_prefix)
        p_layout.addWidget(self._add_prefix_btn)
        p_layout.addWidget(self._rem_prefix_btn)
        layout.addWidget(prefix_box)

        # Suffix & Cleanup
        clean_box = QGroupBox("Cleanup & Suffixes")
        c_layout = QHBoxLayout(clean_box)
        self._rem_suffix_btn = M3Button("Clean (1), (2) Suffixes", variant="outlined")
        self._rem_suffix_btn.clicked.connect(self._run_rem_suffix)
        self._purge_empty_btn = M3Button("Purge Empty Folders", variant="outlined")
        self._purge_empty_btn.clicked.connect(self._run_purge_empty)
        c_layout.addWidget(self._rem_suffix_btn)
        c_layout.addWidget(self._purge_empty_btn)
        layout.addWidget(clean_box)

        # Hierarchy & Flattening
        hier_box = QGroupBox("Hierarchy & Flattening")
        h_layout = QHBoxLayout(hier_box)
        self._move_up_btn = M3Button("Move Files Up One Level", variant="outlined")
        self._move_up_btn.clicked.connect(self._run_move_up)
        self._flatten_root_btn = M3Button("Flatten ALL to Root", variant="outlined")
        self._flatten_root_btn.clicked.connect(self._run_flatten_root)
        h_layout.addWidget(self._move_up_btn)
        h_layout.addWidget(self._flatten_root_btn)
        layout.addWidget(hier_box)

        # Movement
        move_box = QGroupBox("Pattern-Based Movement")
        m_layout = QHBoxLayout(move_box)
        self._organize_btn = M3Button("Organize Into Folders", variant="outlined")
        self._organize_btn.clicked.connect(self._run_organize)
        self._organize_iter_btn = M3Button("Organize (Iterative)", variant="outlined")
        self._organize_iter_btn.clicked.connect(self._run_organize_iter)
        m_layout.addWidget(self._organize_btn)
        m_layout.addWidget(self._organize_iter_btn)
        layout.addWidget(move_box)

        # Workflow & System
        sys_box = QGroupBox("Workflows & System")
        s_layout = QHBoxLayout(sys_box)
        self._workflow_btn = M3Button("Complete Workflow (Prefix + Move Up)", variant="primary")
        self._workflow_btn.clicked.connect(self._run_workflow)
        self._sys_cleanup_btn = M3Button("System Cleanup (Admin)", variant="outlined")
        self._sys_cleanup_btn.clicked.connect(self._run_sys_cleanup)
        s_layout.addWidget(self._workflow_btn)
        s_layout.addWidget(self._sys_cleanup_btn)
        layout.addWidget(sys_box)

        layout.addStretch()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(w)
        return scroll

    # ── Organization Tool Logic ── #

    def _get_org_target(self) -> Optional[Path]:
        target = self._target_input.text()
        if not target:
            self.snackbar_request.emit("Please select a target directory first.", "warning")
            return None
        p = Path(target).resolve()
        if not p.exists():
            self.snackbar_request.emit("Target directory does not exist.", "error")
            return None
        return p

    def _run_add_prefix(self) -> None:
        p = self._get_org_target()
        if not p: return
        from antigravity.tools.file_organizer_toolkit import prefix_files_with_folder
        worker = ToolWorker(prefix_files_with_folder, p, 
                           lambda c: self.snackbar_request.emit(f"Renamed {c} files.", "success"),
                           self.snackbar_request)
        self._pool.start(worker)

    def _run_rem_prefix(self) -> None:
        p = self._get_org_target()
        if not p: return
        from antigravity.tools.file_organizer_toolkit import remove_folder_prefixes
        worker = ToolWorker(remove_folder_prefixes, p, 
                           lambda c: self.snackbar_request.emit(f"Renamed {c} files.", "success"),
                           self.snackbar_request)
        self._pool.start(worker)

    def _run_rem_suffix(self) -> None:
        p = self._get_org_target()
        if not p: return
        from antigravity.tools.file_organizer_toolkit import clean_filename_suffixes
        worker = ToolWorker(clean_filename_suffixes, p, 
                           lambda c: self.snackbar_request.emit(f"Cleaned {c} suffixes.", "success"),
                           self.snackbar_request)
        self._pool.start(worker)

    def _run_purge_empty(self) -> None:
        p = self._get_org_target()
        if not p: return
        from antigravity.tools.file_organizer_toolkit import purge_empty_directories
        worker = ToolWorker(purge_empty_directories, p, 
                           lambda c: self.snackbar_request.emit(f"Deleted {c} empty folders.", "success"),
                           self.snackbar_request)
        self._pool.start(worker)

    def _run_move_up(self) -> None:
        p = self._get_org_target()
        if not p: return
        from antigravity.tools.file_organizer_toolkit import flatten_directory_one_level
        worker = ToolWorker(flatten_directory_one_level, p, 
                           lambda c: self.snackbar_request.emit(f"Moved {c} files up.", "success"),
                           self.snackbar_request)
        self._pool.start(worker)

    def _run_flatten_root(self) -> None:
        p = self._get_org_target()
        if not p: return
        from antigravity.tools.file_organizer_toolkit import flatten_directory_to_root
        worker = ToolWorker(flatten_directory_to_root, p, 
                           lambda c: self.snackbar_request.emit(f"Flattened {c} files to root.", "success"),
                           self.snackbar_request)
        self._pool.start(worker)

    def _run_organize(self) -> None:
        p = self._get_org_target()
        if not p: return
        from antigravity.tools.file_organizer_toolkit import organize_into_folders
        worker = ToolWorker(lambda path: organize_into_folders(path, iterative=False), p, 
                           lambda c: self.snackbar_request.emit(f"Organized {c} files.", "success"),
                           self.snackbar_request)
        self._pool.start(worker)

    def _run_organize_iter(self) -> None:
        p = self._get_org_target()
        if not p: return
        from antigravity.tools.file_organizer_toolkit import organize_into_folders
        worker = ToolWorker(lambda path: organize_into_folders(path, iterative=True), p, 
                           lambda c: self.snackbar_request.emit(f"Organized {c} files (iterative).", "success"),
                           self.snackbar_request)
        self._pool.start(worker)

    def _run_workflow(self) -> None:
        p = self._get_org_target()
        if not p: return
        def workflow(path):
            from antigravity.tools.file_organizer_toolkit import prefix_files_with_folder, flatten_directory_one_level
            a = prefix_files_with_folder(path)
            m = flatten_directory_one_level(path)
            return a + m

        worker = ToolWorker(workflow, p, 
                           lambda c: self.snackbar_request.emit(f"Workflow complete. Ops: {c}", "success"),
                           self.snackbar_request)
        self._pool.start(worker)

    def _run_sys_cleanup(self) -> None:
        from antigravity.tools.file_organizer_toolkit import run_system_cleanup
        success = run_system_cleanup()
        if success:
            self.snackbar_request.emit("System Cleanup launched.", "success")
        else:
            self.snackbar_request.emit("Failed to launch System Cleanup.", "error")




    # ── Helpers ──────────────────────────────────────────────────────────── #

    def _labeled_spin(self, label, mn, mx, val):
        from PyQt6.QtWidgets import QSpinBox
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        lbl = QLabel(label.upper())
        lbl.setProperty("class", "label_primary")
        spin = QSpinBox()
        spin.setMinimum(mn)
        spin.setMaximum(mx)
        spin.setValue(val)
        spin.setMinimumHeight(44)
        layout.addWidget(lbl)
        layout.addWidget(spin)
        return container, spin

    def _labeled_dspin(self, label, mn, mx, val):
        from PyQt6.QtWidgets import QDoubleSpinBox
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        lbl = QLabel(label.upper())
        lbl.setProperty("class", "label_primary")
        spin = QDoubleSpinBox()
        spin.setMinimum(mn)
        spin.setMaximum(mx)
        spin.setValue(val)
        spin.setSuffix(" MB")
        spin.setMinimumHeight(44)
        layout.addWidget(lbl)
        layout.addWidget(spin)
        return container, spin

    def _switch(self, label: str, checked: bool = False) -> QCheckBox:
        cb = QCheckBox(label)
        cb.setChecked(checked)
        cb.setMinimumHeight(32)
        return cb

    def _refresh_recent(self) -> None:
        # Clear current list
        while self._recent_list.count():
            item = self._recent_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        records = self._history_svc.get_all(limit=3)
        if not records:
            lbl = QLabel("No recent scans found.")
            lbl.setProperty("class", "caption")
            self._recent_list.addWidget(lbl)
            return
            
        for r in records:
            row = QHBoxLayout()
            date_str = r["created_at"].strftime("%m/%d %H:%M")
            name = Path(r["root_path"]).name
            lbl = QLabel(f"<b>{name}</b> ({date_str})")
            lbl.setProperty("class", "body_medium")
            row.addWidget(lbl)
            
            open_btn = QPushButton("OPEN")
            open_btn.setFixedSize(60, 24)
            open_btn.setProperty("class", "outlined")
            open_btn.clicked.connect(lambda _, p=r["output_path"]: self._open_path(p))
            row.addWidget(open_btn)
            
            self._recent_list.addLayout(row)

    def _open_path(self, path: str) -> None:
        if Path(path).exists():
            import os, subprocess
            os.startfile(path) if os.name == 'nt' else subprocess.Popen(['xdg-open', str(path)])
        else:
            self.snackbar_request.emit("Path no longer exists.", "warning")

    def _load_defaults(self) -> None:
        s = self._settings
        self._mode_dd.set_value(s.get("last_mode") or s.get("default_mode", "single"))

        self._workers.set_value(str(s.get("default_workers", "4")))
        self._max_files[1].setValue(int(s.get("max_output_files", "5")))
        self._max_mb[1].setValue(float(s.get("max_chunk_mb", "10.0")))
        
        self._skip_hidden_cb.setChecked(s.get("skip_hidden", "true") == "true")
        self._large_files_cb.setChecked(s.get("allow_large_files", "true") == "true")
        self._cleanup_cb.setChecked(s.get("cleanup_before_scan", "false") == "true")
        self._resume_cb.setChecked(s.get("resume", "false") == "true")
        self._incremental_cb.setChecked(s.get("incremental", "false") == "true")
        self._links_cb.setChecked(s.get("follow_links", "false") == "true")
        self._compress_cb.setChecked(s.get("compress", "false") == "true")
        self._dry_run_cb.setChecked(s.get("dry_run", "false") == "true")
        self._verbose_cb.setChecked(s.get("verbose", "false") == "true")
        self._auto_calc_cb.setChecked(s.get("auto_calc", "false") == "true")
        
        self._ignore_file_input.set_text(s.get("ignore_file_name", ".scanignore"))
        
        target = s.get("last_target_path", "")
        if target: self._target_input.set_text(target)
        
        output = s.get("last_output_dir", "")
        if output: self._output_input.set_text(output)

    # ── Scan Logic ────────────────────────────────────────────────────────── #

    def _start_scan(self) -> None:
        """Entry point for the START/STOP button."""
        if self._scan_btn.text() == "STOP ENGINE":
            if hasattr(self, "_current_scanner") and self._current_scanner:
                self._current_scanner.cancel()
                self._scan_btn.setEnabled(False)
                self._scan_btn.setText("STOPPING…")
            return

        try:
            config = self._build_config()
            
            if self._cleanup_cb.isChecked() and config.output_dir and config.output_dir.exists():
                import shutil
                try:
                    for item in list(config.output_dir.iterdir()):
                        try:
                            if item.is_dir():
                                shutil.rmtree(item, ignore_errors=True)
                            else:
                                item.unlink(missing_ok=True)
                        except Exception:
                            pass
                except Exception as e:
                    self.snackbar_request.emit(f"Purge incomplete: {e}", "warning")

            # Persist sticky UI state
            self._settings.set("last_target_path", str(config.root))
            if config.output_dir:
                self._settings.set("last_output_dir", str(config.output_dir))
            self._settings.set("last_mode", config.mode)
            self._settings.set_many({
                "cleanup_before_scan": "true" if self._cleanup_cb.isChecked() else "false",
                "resume": "true" if config.resume else "false",
                "incremental": "true" if config.incremental else "false",
                "follow_links": "true" if config.follow_links else "false",
                "compress": "true" if config.compress else "false",
                "dry_run": "true" if config.dry_run else "false",
                "verbose": "true" if config.verbose else "false",
                "skip_hidden": "true" if config.skip_hidden else "false",
                "allow_large_files": "true" if config.allow_large_files else "false",
                "auto_calc": "true" if config.auto_calc else "false",
                "ignore_file_name": config.ignore_file_name,
            })
            
            # Initiate UI state for scanning
            self._scan_btn.setText("STOP ENGINE")
            self._status_label.setText("SCANNING_IN_PROGRESS")
            self._pulse.show()
            self._console.clear()
            self._progress.indeterminate(True)
            self.scan_started.emit()

            self._current_record_id = self._history_svc.create_record(
                root_path=str(config.root),
                output_path=str(config.output_dir),
                mode=config.mode,
            )

            signals = ScanSignals()
            signals.log.connect(self._on_log)
            signals.progress.connect(self._on_progress)
            signals.finished.connect(self._on_scan_finished)
            signals.error.connect(self._on_error)

            worker = ScanWorker(config, self._current_record_id, signals, parent_view=self)
            self._pool.start(worker)

        except Exception as e:
            self.snackbar_request.emit(str(e), "error")

    def _browse_target(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Target Directory")
        if path:
            self._target_input.set_text(path)
            if not self._output_input.text():
                self._output_input.set_text(str(Path(path) / "scan_output"))

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self._output_input.set_text(path)

    def _open_output(self) -> None:
        path = self._output_input.text()
        if path and Path(path).exists():
            import os, subprocess
            os.startfile(path) if os.name == 'nt' else subprocess.Popen(['xdg-open', str(path)])

    def _clear_console(self) -> None:
        self._console.clear()

    def _build_config(self):
        from antigravity.services.config import ScanConfig
        root = self._target_input.text()
        out  = self._output_input.text()
        if not root:
            raise ValueError("Target directory is required.")

        return ScanConfig(
            root=Path(root),
            output_dir=Path(out) if out else None,
            mode=self._mode_dd.value(),
            max_output_files=self._max_files[1].value(),
            max_chunk_mb=self._max_mb[1].value(),
            follow_links=self._links_cb.isChecked(),
            resume=self._resume_cb.isChecked(),
            incremental=self._incremental_cb.isChecked(),
            skip_hidden=self._skip_hidden_cb.isChecked(),
            allow_large_files=self._large_files_cb.isChecked(),
            ignore_file_name=self._ignore_file_input.text() or ".scanignore",
            workers=int(self._workers.value()),
            compress=self._compress_cb.isChecked(),
            dry_run=self._dry_run_cb.isChecked(),
            verbose=self._verbose_cb.isChecked(),
            auto_calc=self._auto_calc_cb.isChecked(),
            progress=True,
        )


    @pyqtSlot(str)
    def _on_log(self, line: str) -> None:
        self._console.appendPlainText(line)
        self._console.verticalScrollBar().setValue(
            self._console.verticalScrollBar().maximum()
        )
        if "Progress:" in line and "(" in line and "%" in line:
            try:
                pct_str = line.split("(")[1].split("%")[0]
                pct = int(float(pct_str))
                self._on_progress(pct, line.strip())
            except Exception:
                pass

    @pyqtSlot(int, str)
    def _on_progress(self, pct: int, label: str) -> None:
        self._progress.indeterminate(False)
        self._progress.set_progress(pct, label)

    @pyqtSlot(dict)
    def _on_scan_finished(self, summary: dict) -> None:
        self._current_scanner = None
        self._scan_btn.setEnabled(True)
        self._scan_btn.setText("START ENGINE")
        self._status_label.setText("SYSTEM_STABLE")
        self._pulse.hide()
        
        self._stat_files.set_value(f"{summary['files_processed']:,}")
        self._stat_bytes.set_value(self._fmt_bytes(summary['bytes_processed']))
        self._stat_time.set_value(f"{summary['elapsed_seconds']:.1f}s")
        
        if self._current_record_id:
            self._history_svc.complete_record(self._current_record_id, summary)
            
        self.scan_completed.emit(summary)

        self.snackbar_request.emit("Scan completed successfully!", "success")
        self._refresh_recent()

    @pyqtSlot(str)
    def _on_error(self, msg: str) -> None:
        self._current_scanner = None
        self._scan_btn.setEnabled(True)
        self._scan_btn.setText("START ENGINE")
        self._progress.indeterminate(False)
        self._progress.reset()
        if self._current_record_id:
            self._history_svc.fail_record(self._current_record_id, msg)
        self.snackbar_request.emit(f"Error: {msg}", "error")

    @staticmethod
    def _fmt_bytes(b: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if b < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} TB"
