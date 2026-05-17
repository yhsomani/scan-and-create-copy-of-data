from typing import Optional
from PyQt6.QtWidgets import QPushButton, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QPoint, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QPalette
from antigravity.gui.theme import TOKENS, TYPOGRAPHY

class PrimaryButton(QPushButton):
    """A premium electric-purple button with hover scaling and ripple effect."""
    def __init__(self, text: str, parent: Optional[object] = None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(44)
        if parent is not None:
            self.setFont(parent.font())
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {TOKENS['primary']};
                color: white;
                border-radius: 10px;
                font-weight: 600;
                font-size: 14px;
                padding: 0 20px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {TOKENS['primary_muted']};
            }}
            QPushButton:pressed {{
                background-color: {TOKENS['background']};
                border: 1px solid {TOKENS['primary']};
            }}
            QPushButton:disabled {{
                background-color: {TOKENS['surface_elevated']};
                color: {TOKENS['on_surface_tertiary']};
            }}
        """)

class IconButton(QPushButton):
    """Minimalist icon-only button for toolbars."""
    def __init__(self, icon_text: str, parent=None):
        super().__init__(icon_text, parent)
        self.setFixedSize(36, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TOKENS['on_surface_secondary']};
                font-size: 18px;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{
                background: {TOKENS['surface_elevated']};
                color: {TOKENS['on_background']};
            }}
        """)

class SidebarButton(QPushButton):
    """Button optimized for navigation sidebars."""
    def __init__(self, text: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(40)
        self.setText(f"  {icon}   {text}")
        
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TOKENS['on_surface_secondary']};
                text-align: left;
                padding-left: 12px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 500;
                border: none;
            }}
            QPushButton:hover {{
                background: {TOKENS['surface_elevated']};
                color: {TOKENS['on_background']};
                padding-left: 16px;
            }}
            QPushButton:checked {{
                background: {TOKENS['primary_glow']};
                color: {TOKENS['primary']};
                font-weight: 600;
                padding-left: 16px;
                border-left: 3px solid {TOKENS['primary']};
            }}
        """)
