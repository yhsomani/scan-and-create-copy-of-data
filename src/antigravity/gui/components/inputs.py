from typing import Optional, Callable
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QFileDialog
from PyQt6.QtCore import Qt, pyqtSignal
from antigravity.gui.theme import TOKENS, TYPOGRAPHY
from antigravity.gui.components.buttons import IconButton

class LabeledInput(QWidget):
    """A clean, labeled text input."""
    textChanged = pyqtSignal(str)
    
    def __init__(self, label: str, placeholder: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        self.label_lbl = QLabel(label)
        self.label_lbl.setStyleSheet(f"color: {TOKENS['on_surface_secondary']}; font-size: 12px; font-weight: 500;")
        
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.textChanged.connect(self.textChanged.emit)
        
        layout.addWidget(self.label_lbl)
        layout.addWidget(self.edit)

    def text(self) -> str:
        return self.edit.text().strip()
    
    def set_text(self, text: str):
        self.edit.setText(text)

class FilePathInput(LabeledInput):
    """Labeled input with a 'Browse' icon button."""
    def __init__(self, label: str, placeholder: str = "", is_dir: bool = True, parent=None):
        super().__init__(label, placeholder, parent)
        self.is_dir = is_dir
        
        # Replace the layout to add the button
        old_layout = self.layout()
        # Find the line edit
        self.edit.setParent(None)
        
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(self.edit)
        
        self.browse_btn = IconButton("📂")
        self.browse_btn.setToolTip("Browse")
        self.browse_btn.clicked.connect(self._on_browse)
        row.addWidget(self.browse_btn)
        
        old_layout.addLayout(row)

    def _on_browse(self):
        if self.is_dir:
            path = QFileDialog.getExistingDirectory(self, f"Select {self.label_lbl.text()}")
        else:
            path, _ = QFileDialog.getOpenFileName(self, f"Select {self.label_lbl.text()}")
        
        if path:
            self.set_text(path)
