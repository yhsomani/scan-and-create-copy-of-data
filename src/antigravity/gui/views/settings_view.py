from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox, QComboBox, QHBoxLayout
from PyQt6.QtCore import pyqtSignal
from antigravity.gui.theme import TOKENS
from antigravity.gui.components import ActionCard, LabeledInput, PrimaryButton

class SettingsView(QWidget):
    """Global application configuration."""
    save_requested = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        header = QVBoxLayout()
        header.setSpacing(4)
        title = QLabel("System Preferences")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {TOKENS['on_background']};")
        subtitle = QLabel("Customize the scanning engine and user interface defaults.")
        header.addWidget(title)
        header.addWidget(subtitle)
        layout.addLayout(header)

        # UI Settings
        ui_card = ActionCard()
        ui_layout = QVBoxLayout(ui_card)
        ui_layout.setContentsMargins(20, 20, 20, 20)
        ui_layout.setSpacing(16)
        
        ui_title = QLabel("User Interface")
        ui_title.setStyleSheet(f"color: {TOKENS['primary']}; font-weight: bold; font-size: 12px;")
        ui_layout.addWidget(ui_title)
        
        self.cb_animations = QCheckBox("Enable UI Animations")
        self.cb_animations.setChecked(True)
        self.cb_tooltips = QCheckBox("Show Detailed Tooltips")
        self.cb_tooltips.setChecked(True)
        
        ui_layout.addWidget(self.cb_animations)
        ui_layout.addWidget(self.cb_tooltips)
        layout.addWidget(ui_card)

        # Engine Defaults
        eng_card = ActionCard()
        eng_layout = QVBoxLayout(eng_card)
        eng_layout.setContentsMargins(20, 20, 20, 20)
        eng_layout.setSpacing(16)
        
        eng_title = QLabel("Engine Defaults")
        eng_title.setStyleSheet(f"color: {TOKENS['primary']}; font-weight: bold; font-size: 12px;")
        eng_layout.addWidget(eng_title)
        
        self.default_workers = LabeledInput("Default Parallel Workers", "4")
        self.ignore_file = LabeledInput("Global Ignore File Name", ".scanignore")
        
        eng_layout.addWidget(self.default_workers)
        eng_layout.addWidget(self.ignore_file)
        layout.addWidget(eng_card)

        self.btn_save = PrimaryButton("SAVE PREFERENCES")
        self.btn_save.setFixedHeight(44)
        self.btn_save.clicked.connect(self._on_save_clicked)
        layout.addWidget(self.btn_save)
        
        layout.addStretch()

    def set_settings(self, settings: dict):
        self.cb_animations.setChecked(settings.get("ui_animations") == "true")
        self.cb_tooltips.setChecked(settings.get("ui_tooltips") == "true")
        self.default_workers.set_text(settings.get("default_workers", "4"))
        self.ignore_file.set_text(settings.get("ignore_file_name", ".scanignore"))

    def _on_save_clicked(self):
        settings = {
            "ui_animations": "true" if self.cb_animations.isChecked() else "false",
            "ui_tooltips": "true" if self.cb_tooltips.isChecked() else "false",
            "default_workers": self.default_workers.text(),
            "ignore_file_name": self.ignore_file.text(),
        }
        self.save_requested.emit(settings)
