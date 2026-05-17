from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout
from PyQt6.QtCore import pyqtSignal
from antigravity.gui.theme import TOKENS
from antigravity.gui.components import PrimaryButton, ActionCard, FilePathInput

class ToolkitView(QWidget):
    """File organization utilities."""
    tool_requested = pyqtSignal(str, str)  # Tool name, Target path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        header = QVBoxLayout()
        header.setSpacing(4)
        title = QLabel("Universal Toolkit")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {TOKENS['on_background']};")
        subtitle = QLabel("One-click operations to organize, clean, and flatten your workspace.")
        header.addWidget(title)
        header.addWidget(subtitle)
        layout.addLayout(header)

        self.target_input = FilePathInput("Target Workspace", "Directory to organize...")
        layout.addWidget(self.target_input)

        grid = QGridLayout()
        grid.setSpacing(16)

        tools = [
            ("Add Folder Prefix", "prefix_add", "Prepend folder names to filenames."),
            ("Remove Prefix", "prefix_remove", "Strip folder names from filenames."),
            ("Organize (Iterative)", "organize_iter", "Group files by 'Name - file' patterns."),
            ("Flatten to Root", "flatten_root", "Move all nested files to top level."),
            ("Purge Empty Folders", "purge_empty", "Recursive removal of zero-byte folders."),
            ("Deduplicate Files", "deduplicate_files", "Remove exact duplicate files based on SHA-256 hash."),
            ("Rename to Hash", "rename_to_hash", "Rename files to their SHA-256 hash."),
            ("System Cleanup", "sys_cleanup", "Launch Windows admin cleanup utility."),
        ]

        for i, (label, tool_id, desc) in enumerate(tools):
            card = ActionCard()
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 16, 16, 16)
            
            lbl = QLabel(label)
            lbl.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {TOKENS['on_background']};")
            
            sub = QLabel(desc)
            sub.setWordWrap(True)
            sub.setStyleSheet(f"color: {TOKENS['on_surface_secondary']}; font-size: 11px;")
            
            btn = PrimaryButton("EXECUTE")
            btn.setFixedHeight(32)
            btn.setStyleSheet(btn.styleSheet().replace("height: 44px;", "height: 32px;"))
            btn.clicked.connect(lambda _, tid=tool_id: self.tool_requested.emit(tid, self.target_input.text()))
            
            card_layout.addWidget(lbl)
            card_layout.addWidget(sub)
            card_layout.addSpacing(8)
            card_layout.addWidget(btn)
            
            grid.addWidget(card, i // 2, i % 2)

        layout.addLayout(grid)
        layout.addStretch()
