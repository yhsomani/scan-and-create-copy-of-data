from typing import Optional
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from antigravity.gui.theme import TOKENS, TYPOGRAPHY

class StatCard(QFrame):
    """A glassmorphic card for displaying metrics (e.g. Files, Bytes)."""
    def __init__(self, title: str, value: str = "0", subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setMinimumWidth(160)
        self.setFixedHeight(100)
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {TOKENS['surface']};
                border: 1px solid {TOKENS['border']};
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        self.title_lbl = QLabel(title.upper())
        self.title_lbl.setStyleSheet(f"color: {TOKENS['on_surface_secondary']}; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        
        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(f"color: {TOKENS['on_background']}; font-size: 24px; font-weight: 600;")
        
        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setStyleSheet(f"color: {TOKENS['on_surface_tertiary']}; font-size: 11px;")
        
        layout.addWidget(self.title_lbl)
        layout.addWidget(self.value_lbl)
        if subtitle:
            layout.addWidget(self.sub_lbl)
        else:
            layout.addStretch()

    def update_value(self, val: str):
        self.value_lbl.setText(val)

class ActionCard(QFrame):
    """A container card with a subtle hover shadow for grouping settings."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {TOKENS['surface_elevated']};
                border: 1px solid {TOKENS['border']};
                border-radius: 16px;
            }}
        """)
        
        # Shadow Effect
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QColor(0, 0, 0, 80))
        self.shadow.setOffset(0, 4)
        self.setGraphicsEffect(self.shadow)
