from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QGridLayout, QCheckBox
from PyQt6.QtCore import Qt, pyqtSignal
from antigravity.gui.theme import TOKENS, TYPOGRAPHY
from antigravity.gui.components import PrimaryButton, StatCard, ActionCard, FilePathInput, LabeledInput
from antigravity.gui.components.misc import PulseIndicator

class ScannerView(QWidget):
    """The primary engine control center."""
    start_requested = pyqtSignal(dict)  # Emits config dict
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)

        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        
        title_row = QHBoxLayout()
        title = QLabel("Engine Control")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {TOKENS['on_background']};")
        self.pulse = PulseIndicator()
        self.pulse.hide()
        
        title_row.addWidget(title)
        title_row.addWidget(self.pulse)
        title_row.addStretch()
        header_layout.addLayout(title_row)
        
        subtitle = QLabel("Configure and execute high-speed directory analysis.")
        subtitle.setStyleSheet(f"color: {TOKENS['on_surface_secondary']}; font-size: 13px;")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        # Stats Overview
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)
        self.files_stat = StatCard("Files Analyzed", "0")
        self.bytes_stat = StatCard("Data Processed", "0 MB")
        self.time_stat = StatCard("Time Elapsed", "0.0s")
        stats_layout.addWidget(self.files_stat)
        stats_layout.addWidget(self.bytes_stat)
        stats_layout.addWidget(self.time_stat)
        main_layout.addLayout(stats_layout)

        # Configuration Area
        config_grid = QHBoxLayout()
        config_grid.setSpacing(20)

        # Left Column: Paths & Core Settings
        left_col = QVBoxLayout()
        left_col.setSpacing(16)
        
        path_card = ActionCard()
        path_layout = QVBoxLayout(path_card)
        path_layout.setContentsMargins(20, 20, 20, 20)
        path_layout.setSpacing(16)
        
        self.target_input = FilePathInput("Target Directory", "Path to source code...")
        self.output_input = FilePathInput("Output Location", "Where to save results...")
        self.search_input = LabeledInput("Regex Search Patterns", "Comma separated patterns (e.g., TODO, FIXME, ^def)")
        
        path_layout.addWidget(self.target_input)
        path_layout.addWidget(self.output_input)
        path_layout.addWidget(self.search_input)
        left_col.addWidget(path_card)
        
        config_grid.addLayout(left_col, 3)

        # Right Column: Engine Toggles
        right_col = QVBoxLayout()
        right_col.setSpacing(16)
        
        engine_card = ActionCard()
        engine_layout = QVBoxLayout(engine_card)
        engine_layout.setContentsMargins(20, 20, 20, 20)
        engine_layout.setSpacing(12)
        
        engine_title = QLabel("Engine Parameters")
        engine_title.setStyleSheet(f"color: {TOKENS['primary']}; font-weight: bold; font-size: 12px; margin-bottom: 4px;")
        engine_layout.addWidget(engine_title)
        
        self.cb_compress = QCheckBox("Gzip Compression")
        self.cb_hidden = QCheckBox("Include Hidden Files")
        self.cb_links = QCheckBox("Follow Symlinks")
        self.cb_dry = QCheckBox("Dry Run Mode")
        
        for cb in [self.cb_compress, self.cb_hidden, self.cb_links, self.cb_dry]:
            engine_layout.addWidget(cb)
            
        right_col.addWidget(engine_card)
        config_grid.addLayout(right_col, 2)

        main_layout.addLayout(config_grid)

        # Footer Action
        main_layout.addStretch()
        
        self.scan_btn = PrimaryButton("INITIATE SCAN SEQUENCE")
        self.scan_btn.setFixedHeight(56)
        self.scan_btn.clicked.connect(self._on_scan_clicked)
        main_layout.addWidget(self.scan_btn)

    def _on_scan_clicked(self):
        config = {
            "root": self.target_input.text(),
            "output_dir": self.output_input.text(),
            "compress": self.cb_compress.isChecked(),
            "skip_hidden": not self.cb_hidden.isChecked(),
            "follow_links": self.cb_links.isChecked(),
            "dry_run": self.cb_dry.isChecked(),
            "search_patterns": [p.strip() for p in self.search_input.text().split(",")] if self.search_input.text() else [],
        }
        self.start_requested.emit(config)

    def update_metrics(self, summary: dict):
        self.files_stat.update_value(f"{summary.get('files_processed', 0):,}")
        self.bytes_stat.update_value(f"{summary.get('bytes_processed', 0) / (1024*1024):.1f} MB")
        self.time_stat.update_value(f"{summary.get('elapsed_seconds', 0.0):.1f}s")
