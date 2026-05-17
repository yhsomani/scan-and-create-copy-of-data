from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QPainter, QColor
from antigravity.gui.theme import TOKENS

class PulseIndicator(QWidget):
    """Animated pulse for scanning state."""
    def __init__(self, parent=None):
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

    @pyqtProperty(float)
    def pulse_prop(self) -> float:
        return self._pulse_val

    @pulse_prop.setter
    def pulse_prop(self, val: float):
        self._pulse_val = val
        self._radius = 2 + (val * 8)
        self._opacity = 1.0 - val
        self.update()

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
