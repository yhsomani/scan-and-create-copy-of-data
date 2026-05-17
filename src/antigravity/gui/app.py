import sys
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QStackedWidget, QLabel, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSlot
from antigravity.gui.theme import TOKENS, TYPOGRAPHY, get_stylesheet
from antigravity.gui.components import SidebarButton, IconButton
from antigravity.gui.views.scanner_view import ScannerView
from antigravity.gui.views.toolkit_view import ToolkitView
from antigravity.gui.views.history_view import HistoryView
from antigravity.gui.views.settings_view import SettingsView
from antigravity.gui.controllers import AppController
from PyQt6.QtWidgets import QPlainTextEdit

class AntigravityShell(QMainWindow):
    """The high-performance application shell."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Antigravity Scanner v4.5")
        self.resize(1100, 750)
        self.setup_ui()
        self.setStyleSheet(get_stylesheet())
        self.controller = AppController(self)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(240)
        self.sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {TOKENS['surface']};
                border-right: 1px solid {TOKENS['border']};
            }}
        """)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(16, 24, 16, 24)
        sidebar_layout.setSpacing(8)

        # App Logo / Title
        logo_area = QHBoxLayout()
        logo_label = QLabel("🚀")
        logo_label.setStyleSheet("font-size: 24px;")
        logo_text = QLabel("ANTIGRAVITY")
        logo_text.setStyleSheet(f"font-weight: 800; font-size: 16px; letter-spacing: 2px; color: {TOKENS['on_background']};")
        logo_area.addWidget(logo_label)
        logo_area.addWidget(logo_text)
        logo_area.addStretch()
        sidebar_layout.addLayout(logo_area)
        sidebar_layout.addSpacing(32)

        # Navigation Groups
        nav_label = QLabel("ANALYTICS")
        nav_label.setStyleSheet(f"color: {TOKENS['on_surface_tertiary']}; font-size: 10px; font-weight: bold; margin-left: 12px;")
        sidebar_layout.addWidget(nav_label)

        self.btn_scanner = SidebarButton("Scanner", "🔍")
        self.btn_scanner.setChecked(True)
        self.btn_scanner.clicked.connect(lambda: self.switch_view(0))
        
        self.btn_toolkit = SidebarButton("Toolkit", "🛠️")
        self.btn_toolkit.clicked.connect(lambda: self.switch_view(1))
        
        self.btn_history = SidebarButton("History", "📜")
        self.btn_history.clicked.connect(lambda: self.switch_view(2))

        sidebar_layout.addWidget(self.btn_scanner)
        sidebar_layout.addWidget(self.btn_toolkit)
        sidebar_layout.addWidget(self.btn_history)
        
        sidebar_layout.addSpacing(24)
        pref_label = QLabel("PREFERENCES")
        pref_label.setStyleSheet(nav_label.styleSheet())
        sidebar_layout.addWidget(pref_label)
        
        self.btn_settings = SidebarButton("Settings", "⚙️")
        self.btn_settings.clicked.connect(lambda: self.switch_view(3))
        sidebar_layout.addWidget(self.btn_settings)

        sidebar_layout.addStretch()
        
        # User / System Status at bottom
        status_card = QFrame()
        status_card.setStyleSheet(f"background: {TOKENS['surface_elevated']}; border-radius: 10px; padding: 12px;")
        sc_layout = QVBoxLayout(status_card)
        sc_layout.setContentsMargins(12, 12, 12, 12)
        sys_lbl = QLabel("SYSTEM_READY")
        sys_lbl.setStyleSheet(f"color: {TOKENS['success']}; font-size: 10px; font-weight: bold;")
        sc_layout.addWidget(sys_lbl)
        sidebar_layout.addWidget(status_card)

        main_layout.addWidget(self.sidebar)

        # ── View Stack ────────────────────────────────────────────────────────
        self.content_stack = QStackedWidget()
        
        self.view_scanner = ScannerView()
        self.view_toolkit = ToolkitView()
        self.view_history = HistoryView()
        self.view_settings = SettingsView()
        
        self.content_stack.addWidget(self.view_scanner)
        self.content_stack.addWidget(self.view_toolkit)
        self.content_stack.addWidget(self.view_history)
        self.content_stack.addWidget(self.view_settings)
        
        main_layout.addWidget(self.content_stack)

        # ── Console (Overlay-ish) ─────────────────────────────────────────────
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(150)
        self.console.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {TOKENS['background']};
                color: {TOKENS['success']};
                font-family: "{TYPOGRAPHY['code']['family']}";
                font-size: {TYPOGRAPHY['code']['size']}px;
                border: none;
                border-top: 1px solid {TOKENS['border']};
            }}
        """)
        
        # Add to a vertical layout that wraps the content stack
        content_container = QWidget()
        cc_layout = QVBoxLayout(content_container)
        cc_layout.setContentsMargins(0, 0, 0, 0)
        cc_layout.setSpacing(0)
        cc_layout.addWidget(self.content_stack)
        cc_layout.addWidget(self.console)
        
        main_layout.addWidget(content_container)

    def switch_view(self, index: int):
        self.content_stack.setCurrentIndex(index)
        # Update sidebar buttons
        buttons = [self.btn_scanner, self.btn_toolkit, self.btn_history, self.btn_settings]
        for i, btn in enumerate(buttons):
            btn.setChecked(i == index)

    def append_log(self, text: str):
        """Thread-safe log appending."""
        self.console.appendPlainText(text)
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

def main():
    app = QApplication(sys.argv)
    window = AntigravityShell()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
