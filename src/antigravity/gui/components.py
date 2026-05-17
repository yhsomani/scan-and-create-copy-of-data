"""
Apple-styled UI components for PyQt6.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from PyQt6.QtCore import (
    QEasingCurve, QPropertyAnimation, QSize, Qt, QTimer, pyqtSignal, pyqtProperty
)
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPalette
from PyQt6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QSlider, QSpacerItem, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QProgressBar, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QSplitter, QTextEdit,
    QGraphicsOpacityEffect
)

from antigravity.gui.theme import TOKENS, TYPOGRAPHY


def _c() -> dict:
    return TOKENS


# ──────────────────────────── Stat Card ──────────────────────────────────────── #

class StatCard(QFrame):
    """Apple-style stat card: title + large value + optional subtitle."""

    def __init__(
        self,
        title: str,
        value: str = "0",
        subtitle: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setMinimumHeight(110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(8)

        self._title_label = QLabel(title.upper())
        self._title_label.setStyleSheet(
            f"color: {TOKENS['on_surface_secondary']}; "
            f"font-size: {TYPOGRAPHY['caption_bold']['size']}px; "
            f"font-weight: {TYPOGRAPHY['caption_bold']['weight']};"
        )

        self._value_label = QLabel(value)
        self._value_label.setObjectName("stat_value")
        font = QFont("SF Pro Display", 28, QFont.Weight.Bold)
        self._value_label.setFont(font)
        self._value_label.setStyleSheet(f"color: {TOKENS['on_background']};")
        self._value_label.setWordWrap(True)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._sub_label = QLabel(subtitle)
        self._sub_label.setStyleSheet(
            f"color: {TOKENS['primary']}; "
            f"font-size: {TYPOGRAPHY['caption']['size']}px; "
            f"font-weight: {TYPOGRAPHY['caption']['weight']};"
        )

        layout.addWidget(self._title_label)
        layout.addWidget(self._value_label)
        if subtitle:
            layout.addWidget(self._sub_label)

    def set_value(self, value: str) -> None:
        self._value_label.setText(value)

    def set_subtitle(self, text: str) -> None:
        self._sub_label.setText(text)


# ──────────────────────────── Section Header ──────────────────────────────── #

class SectionHeader(QWidget):
    """Apple section header: headline + optional action button."""

    def __init__(
        self,
        title: str,
        action_label: str = "",
        action_callback: Optional[Callable] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"font-size: {TYPOGRAPHY['display_section']['size']}px; "
            f"font-weight: {TYPOGRAPHY['display_section']['weight']}; "
            f"color: {TOKENS['on_background']};"
        )
        layout.addWidget(title_lbl)
        layout.addStretch()

        if action_label and action_callback:
            btn = AppleButton(action_label, variant="outlined")
            btn.clicked.connect(action_callback)
            layout.addWidget(btn)


# ──────────────────────────── Apple Button ──────────────────────────────────────────── #

class AppleButton(QPushButton):
    """Primary, pill, or outlined Apple button."""

    def __init__(
        self,
        label: str,
        variant: str = "primary",  # primary | pill | outlined | nav
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(label, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if variant == "primary":
            self.setMinimumHeight(40)
        elif variant == "pill":
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {TOKENS['link_dark']};
                    border: 1px solid {TOKENS['link_dark']};
                    border-radius: 980px;
                    padding: 8px 16px;
                    font-size: {TYPOGRAPHY['button']['size']}px;
                }}
                QPushButton:hover {{
                    text-decoration: underline;
                }}
            """)
        elif variant == "outlined":
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: 1px solid {TOKENS['on_surface_secondary']};
                    color: {TOKENS['on_background']};
                    border-radius: 8px;
                    padding: 8px 15px;
                    font-size: {TYPOGRAPHY['button']['size']}px;
                }}
                QPushButton:hover {{
                    background-color: {TOKENS['surface_4']};
                }}
            """)
        elif variant == "nav":
            self.setMinimumHeight(44)
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {TOKENS['on_surface_secondary']};
                    text-align: left;
                    padding-left: 16px;
                    border-radius: 8px;
                    font-size: {TYPOGRAPHY['nav']['size']}px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {TOKENS['surface_3']};
                }}
                QPushButton:checked {{
                    background-color: {TOKENS['surface_3']};
                    color: {TOKENS['on_background']};
                }}
            """)


# ──────────────────────────── Labeled Input ───────────────────────────────── #

class AppleInput(QWidget):
    """Labeled text input with optional browse button."""

    textChanged = pyqtSignal(str)
    returnPressed = pyqtSignal()

    def __init__(
        self,
        label: str,
        placeholder: str = "",
        browse: bool = False,
        browse_callback: Optional[Callable] = None,
        is_password: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            f"color: {TOKENS['primary']}; "
            f"font-size: {TYPOGRAPHY['caption_bold']['size']}px; "
            f"font-weight: {TYPOGRAPHY['caption_bold']['weight']};"
        )
        layout.addWidget(lbl)

        row = QHBoxLayout()
        row.setSpacing(8)

        self._edit = QLineEdit()
        self._edit.setPlaceholderText(placeholder or f"Enter {label}...")
        self._edit.setMinimumHeight(48)
        if is_password:
            self._edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._edit.textChanged.connect(self.textChanged.emit)
        self._edit.returnPressed.connect(self.returnPressed.emit)
        row.addWidget(self._edit)

        if browse and browse_callback:
            btn = AppleButton("Browse", variant="outlined")
            btn.setFixedWidth(90)
            btn.clicked.connect(browse_callback)
            row.addWidget(btn)

        layout.addLayout(row)

    def text(self) -> str:
        return self._edit.text().strip()

    def set_text(self, t: str) -> None:
        self._edit.setText(t)

    def clear(self) -> None:
        self._edit.clear()


# ──────────────────────────── Apple Dropdown ───────────────────────────── #

class AppleDropdown(QWidget):
    """Labeled dropdown selector."""

    currentTextChanged = pyqtSignal(str)

    def __init__(
        self,
        label: str,
        options: List[str],
        current: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            f"color: {TOKENS['primary']}; "
            f"font-size: {TYPOGRAPHY['caption_bold']['size']}px; "
            f"font-weight: {TYPOGRAPHY['caption_bold']['weight']};"
        )
        layout.addWidget(lbl)

        self._combo = QComboBox()
        self._combo.addItems(options)
        self._combo.setMinimumHeight(44)
        if current in options:
            self._combo.setCurrentText(current)
        self._combo.currentTextChanged.connect(self.currentTextChanged.emit)
        layout.addWidget(self._combo)

    def value(self) -> str:
        return self._combo.currentText()

    def set_value(self, v: any) -> None:
        self._combo.setCurrentText(str(v))


# ──────────────────────────── Apple Slider ─────────────────────────────────── #




# ──────────────────────────── Separator ───────────────────────────────────── #

class Separator(QFrame):
    def __init__(
        self, orientation: str = "h", parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        if orientation == "h":
            self.setFrameShape(QFrame.Shape.HLine)
        else:
            self.setFrameShape(QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setStyleSheet(f"color: {TOKENS['surface_3']};")


# ──────────────────────────── Apple Table ─────────────────────────────────── #

class AppleTable(QTableWidget):
    """Apple-styled table with proper headers."""

    def __init__(
        self,
        columns: List[Tuple[str, int]],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels([c[0] for c in columns])
        for i, (_, w) in enumerate(columns):
            self.setColumnWidth(i, w)

        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.horizontalHeader().setStretchLastSection(True)

    def set_rows(self, rows: List[List[str]]) -> None:
        self.setRowCount(0)
        for row_data in rows:
            row = self.rowCount()
            self.insertRow(row)
            for col, val in enumerate(row_data):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.setItem(row, col, item)
            self.setRowHeight(row, 52)


# ──────────────────────────── Search Bar ──────────────────────────────────────────── #

class SearchBar(QLineEdit):
    def __init__(
        self, placeholder: str = "Search...", parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(42)
        self.setClearButtonEnabled(True)
        self.setStyleSheet(f"""
            QLineEdit {{
                background-color: {TOKENS['surface_4']};
                color: {TOKENS['on_background']};
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
            }}
            QLineEdit::placeholder {{
                color: {TOKENS['on_surface_tertiary']};
            }}
        """)


# ──────────────────────────── Copy Button ────────────────────────────────── #

class CopyButton(QPushButton):
    """Icon button to copy text to clipboard."""
    def __init__(self, target_widget, parent=None):
        super().__init__("📋", parent)
        self.setFixedSize(32, 32)
        self.setToolTip("Copy to Clipboard")
        self.clicked.connect(lambda: self._copy(target_widget))
        
    def _copy(self, target):
        if hasattr(target, "toPlainText"):
            text = target.toPlainText()
        elif hasattr(target, "text"):
            text = target.text()
        else:
            return
        QApplication.clipboard().setText(text)


# ──────────────────────────── Progress Row ──────────────────────────────────────────── #

class ProgressRow(QWidget):
    """Progress bar + status label."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._bar = QProgressBar()
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        self._bar.setValue(0)
        layout.addWidget(self._bar)

        self._label = QLabel("Ready")
        self._label.setStyleSheet(f"color: {TOKENS['on_surface_secondary']};")
        self._label.setFixedWidth(160)
        layout.addWidget(self._label)

    def set_progress(self, value: int, label: str = "") -> None:
        self._bar.setValue(value)
        if label:
            self._label.setText(label)

    def reset(self) -> None:
        self._bar.setValue(0)
        self._label.setText("Ready")

    def indeterminate(self, active: bool) -> None:
        if active:
            self._bar.setRange(0, 0)
        else:
            self._bar.setRange(0, 100)


# ──────────────────────────── Pulse Indicator ────────────────────────────────── #

class PulseIndicator(QWidget):
    """Animated pulse for scanning state."""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self._radius = 2
        self._opacity = 1.0
        self._pulse_val = 0.0
        
        self._anim = QPropertyAnimation(self, b"pulse_prop")
        self._anim.setDuration(1500)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setLoopCount(-1)
        self._anim.start()

    def get_pulse_prop(self) -> float:
        return self._pulse_val

    def set_pulse_prop(self, val: float):
        self._pulse_val = val
        self._radius = 2 + (val * 8)
        self._opacity = 1.0 - val
        self.update()
    
    pulse_prop = pyqtProperty(float, fget=get_pulse_prop, fset=set_pulse_prop)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Core dot
        p.setBrush(QColor(TOKENS['primary']))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(10, 10, 4, 4)
        
        # Pulse ring
        if self._opacity > 0:
            color = QColor(TOKENS['primary'])
            color.setAlphaF(self._opacity)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(color)
            p.drawEllipse(int(12-self._radius), int(12-self._radius), int(self._radius*2), int(self._radius*2))


# ─────────────────────────────────── M3 Aliases ─────────────────────────────────── #

M3Button = AppleButton
M3Input = AppleInput
M3Dropdown = AppleDropdown

M3Table = AppleTable
SectionHeader = SectionHeader
Separator = Separator
StatCard = StatCard
PulseIndicator = PulseIndicator
ProgressRow = ProgressRow
SearchBar = SearchBar
CopyButton = CopyButton


# ─────────────────────────────────── Snackbar ─────────────────────────────────── #

class Snackbar(QFrame):
    """Apple-style snackbar notification."""

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.hide)
        self._build_ui()

    def _build_ui(self) -> None:
        self.setFixedHeight(48)
        self.setFixedWidth(280)
        self.setStyleSheet(f"""
            QFrame {{
                background: {TOKENS['surface_4']};
                border-radius: 8px;
                border: 1px solid {TOKENS['on_surface_tertiary']};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)

        self._label = QLabel()
        self._label.setStyleSheet(f"color: {TOKENS['on_background']};")
        layout.addWidget(self._label)

        layout.addStretch()

    def show_message(self, text: str, type: str = "info") -> None:
        colors = {
            "success": TOKENS['primary'],
            "error": TOKENS['error'],
            "info": TOKENS['on_surface_secondary'],
        }
        self._label.setStyleSheet(f"color: {colors.get(type, colors['info'])};")
        self._label.setText(text)
        self.show()
        self._timer.start(3000)