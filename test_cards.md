# test_deck::test2

## What is a boolean?

<!-- notecardId: 1776343901844 -->
A data type that can only have one of two values: `true` or `false`.

## How do you write a single-line comment in Python?


<!-- notecardId: 1776343901850 -->
You use the hash symbol `#`.

## test python. 

<!-- notecardId: 1776343901852 -->
```python
print("Hello World")
x = 1
y = True
z = Nothing
z1 = Everythin
```

```python
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
```