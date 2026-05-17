from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit
from PyQt6.QtCore import Qt
from antigravity.gui.theme import TOKENS
from antigravity.gui.components import ActionCard, IconButton

class HistoryView(QWidget):
    """Browsing past scan records."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        header = QVBoxLayout()
        header.setSpacing(4)
        title = QLabel("Scan History")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {TOKENS['on_background']};")
        subtitle = QLabel("Review past analysis reports and re-access generated output files.")
        header.addWidget(title)
        header.addWidget(subtitle)
        layout.addLayout(header)

        card = ActionCard()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(1, 1, 1, 1) # Table takes full width
        
        # Search Bar
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(16, 16, 16, 8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search history (e.g., target name, date)...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {TOKENS['surface']};
                color: {TOKENS['on_surface']};
                padding: 10px;
                border: 1px solid {TOKENS['border']};
                border-radius: 6px;
            }}
        """)
        self.search_input.textChanged.connect(self._filter_table)
        search_layout.addWidget(self.search_input)
        card_layout.addLayout(search_layout)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Date", "Target", "Mode", "Size", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {TOKENS['surface_elevated']};
                border: none;
                gridline-color: transparent;
                border-radius: 12px;
            }}
            QHeaderView::section {{
                background-color: {TOKENS['surface']};
                color: {TOKENS['on_surface_secondary']};
                padding: 12px;
                border: none;
                font-weight: bold;
                font-size: 11px;
            }}
            QTableWidget::item {{
                padding: 12px;
                border-bottom: 1px solid {TOKENS['border']};
            }}
        """)
        
        self.table.setSortingEnabled(True)
        card_layout.addWidget(self.table)
        layout.addWidget(card)
        
        layout.addStretch()

    def set_records(self, records: list):
        self.table.setRowCount(len(records))
        for i, rec in enumerate(records):
            self.table.setItem(i, 0, QTableWidgetItem(rec.get("date", "")))
            self.table.setItem(i, 1, QTableWidgetItem(rec.get("name", "")))
            self.table.setItem(i, 2, QTableWidgetItem(rec.get("mode", "")))
            self.table.setItem(i, 3, QTableWidgetItem(rec.get("size", "")))
            
            # Actions cell
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(8)
            
            open_btn = IconButton("📂")
            open_btn.setToolTip("Open Folder")
            actions_layout.addWidget(open_btn)
            
            del_btn = IconButton("🗑️")
            del_btn.setToolTip("Delete Record")
            actions_layout.addWidget(del_btn)
            
            self.table.setCellWidget(i, 4, actions_widget)
            
    def _filter_table(self, text: str):
        search_term = text.lower()
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount() - 1): # Exclude actions column
                item = self.table.item(row, col)
                if item and search_term in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)
