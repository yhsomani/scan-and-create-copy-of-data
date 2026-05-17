"""
Antigravity Design System (ADS)
===============================
A modern, premium design system for high-performance desktop tools.
Inspired by Apple's Human Interface Guidelines and Microsoft's Fluent Design.
"""

# ── Color Palette ─────────────────────────────────────────────────────────────

TOKENS = {
    # Backgrounds
    "background": "#0A0A0B",        # Deep space black
    "surface": "#141416",           # Main cards
    "surface_elevated": "#1C1C1F", # Elevated elements
    "surface_glass": "rgba(25, 25, 28, 0.75)", # Translucent elements
    
    # Brand Colors
    "primary": "#7000FF",           # Electric Purple
    "primary_muted": "#40008F",
    "primary_glow": "rgba(112, 0, 255, 0.3)",
    
    # Accents
    "accent": "#00F0FF",            # Cyan Neo
    "success": "#00E676",
    "warning": "#FFD600",
    "error": "#FF5252",
    
    # Typography & Icons
    "on_background": "#F5F5F7",     # Off-white primary text
    "on_surface": "#EBEBF5",
    "on_surface_secondary": "rgba(235, 235, 245, 0.6)",
    "on_surface_tertiary": "rgba(235, 235, 245, 0.3)",
    
    # Borders & Dividers
    "border": "rgba(255, 255, 255, 0.08)",
    "border_strong": "rgba(255, 255, 255, 0.15)",
}

# ── Typography ────────────────────────────────────────────────────────────────

TYPOGRAPHY = {
    "display": {
        "family": "Inter, SF Pro Display, Segoe UI",
        "size": 32,
        "weight": "bold"
    },
    "h1": {
        "family": "Inter, SF Pro Display, Segoe UI",
        "size": 24,
        "weight": "600"
    },
    "h2": {
        "family": "Inter, SF Pro Display, Segoe UI",
        "size": 18,
        "weight": "600"
    },
    "body": {
        "family": "Inter, SF Pro Text, Segoe UI",
        "size": 14,
        "weight": "normal"
    },
    "caption": {
        "family": "Inter, SF Pro Text, Segoe UI",
        "size": 12,
        "weight": "normal"
    },
    "code": {
        "family": "JetBrains Mono, Fira Code, Consolas",
        "size": 13,
        "weight": "normal"
    }
}

# ── Animation Tokens ─────────────────────────────────────────────────────────

ANIMATIONS = {
    "duration_fast": 200,
    "duration_normal": 350,
    "easing": "OutCubic"
}

# ── Global Stylesheet ─────────────────────────────────────────────────────────

def get_stylesheet() -> str:
    """Returns the core QSS for the application."""
    return f"""
    QMainWindow, QWidget {{
        background-color: {TOKENS['background']};
        color: {TOKENS['on_background']};
        font-family: "{TYPOGRAPHY['body']['family']}";
        font-size: {TYPOGRAPHY['body']['size']}px;
    }}

    /* Scrollbars */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {TOKENS['on_surface_tertiary']};
        min-height: 20px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {TOKENS['on_surface_secondary']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    /* Input Fields */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {TOKENS['surface_elevated']};
        border: 1px solid {TOKENS['border']};
        border-radius: 8px;
        padding: 8px 12px;
        color: {TOKENS['on_background']};
        selection-background-color: {TOKENS['primary']};
    }}
    QLineEdit:focus {{
        border: 1px solid {TOKENS['primary']};
    }}

    /* Group Boxes */
    QGroupBox {{
        font-weight: bold;
        border: 1px solid {TOKENS['border']};
        border-radius: 12px;
        margin-top: 1.5em;
        padding-top: 1em;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 5px;
        color: {TOKENS['on_surface_secondary']};
    }}

    /* Tabs */
    QTabWidget::pane {{
        border: none;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {TOKENS['on_surface_secondary']};
        padding: 8px 16px;
        margin-right: 4px;
        font-weight: 500;
    }}
    QTabBar::tab:selected {{
        color: {TOKENS['primary']};
        border-bottom: 2px solid {TOKENS['primary']};
    }}
    """