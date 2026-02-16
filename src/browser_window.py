import sqlite3
import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QLabel)
from PyQt6.QtCore import Qt

DB_PATH = 'vocabook.db'

class BrowserWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vocabook Browser")
        self.resize(900, 600)
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Search Bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to filter...")
        self.search_input.textChanged.connect(self.filter_data)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Word", "Definition", "State", "Due Date", "Stability", "Difficulty", "Reps"
        ])
        
        # Style
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Word
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)          # Definition
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # State
        
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)
        
        # State Mapping
        self.state_map = {
            0: "New",
            1: "Learning",
            2: "Review",
            3: "Relearning"
        }

    def load_data(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Fetch all words
        cursor.execute("""
            SELECT word, definition, state, due, stability, difficulty, reps 
            FROM words
        """)
        rows = cursor.fetchall()
        conn.close()
        
        self.all_rows = rows
        self.populate_table(rows)

    def populate_table(self, rows):
        self.table.setSortingEnabled(False) # Disable during populate
        self.table.setRowCount(len(rows))
        
        for i, row in enumerate(rows):
            word, definition, state, due, stability, difficulty, reps = row
            
            # 0. Word
            self.table.setItem(i, 0, QTableWidgetItem(str(word)))
            
            # 1. Definition (Truncate?)
            def_text = str(definition) if definition else ""
            # if len(def_text) > 100: def_text = def_text[:100] + "..."
            self.table.setItem(i, 1, QTableWidgetItem(def_text))
            
            # 2. State
            state_str = self.state_map.get(state, "New")
            self.table.setItem(i, 2, QTableWidgetItem(state_str))
            
            # 3. Due Date
            due_str = ""
            if due:
                try:
                    # Parse ISO string
                    dt = datetime.datetime.fromisoformat(due)
                    due_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    due_str = str(due)
            self.table.setItem(i, 3, QTableWidgetItem(due_str))
            
            # 4. Stability (Float, create custom item for numeric sort?)
            st_item = QTableWidgetItem()
            st_item.setData(Qt.ItemDataRole.DisplayRole, round(stability, 2) if stability else 0.0)
            self.table.setItem(i, 4, st_item)
            
            # 5. Difficulty
            diff_item = QTableWidgetItem()
            diff_item.setData(Qt.ItemDataRole.DisplayRole, round(difficulty, 2) if difficulty else 0.0)
            self.table.setItem(i, 5, diff_item)
            
            # 6. Reps
            reps_item = QTableWidgetItem()
            reps_item.setData(Qt.ItemDataRole.DisplayRole, reps if reps else 0)
            self.table.setItem(i, 6, reps_item)

        self.table.setSortingEnabled(True)

    def filter_data(self):
        query = self.search_input.text().lower()
        if not query:
            self.populate_table(self.all_rows)
            return
            
        filtered = []
        for row in self.all_rows:
            # Search in Word (0) or Definition (1)
            w = str(row[0]).lower()
            d = str(row[1]).lower() if row[1] else ""
            if query in w or query in d:
                filtered.append(row)
        
        self.populate_table(filtered)
