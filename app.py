import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QComboBox, QPushButton, 
                             QTextEdit, QGroupBox, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
import threading
from src.calibre_db import CalibreDB
from src.bulk_highlighter import process_book

# Configuration
LIBRARY_PATH = '/Users/karthiktalluri/Calibre Library'

class WorkerThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    log_signal = pyqtSignal(str)

    def __init__(self, book_id, start_cfi, end_cfi):
        super().__init__()
        self.book_id = book_id
        self.start_cfi = start_cfi
        self.end_cfi = end_cfi

    def run(self):
        try:
            # We need to capture stdout/stderr in this thread too?
            # Or just let the redirection work globally.
            # Since standard prints go to sys.stdout, and we redirect that in main, it works.
            process_book(self.book_id, self.start_cfi, self.end_cfi)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class StreamRedirect:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, text):
        # Must update GUI from main thread? 
        # Actually QTextEdit append is thread-safe effectively via signals internally in Qt usually?
        # No, strict Qt rule: GUI updates only from Main Thread.
        # We need a signal mechanism for robust logging.
        # However, for simplicity using QMetaObject.invokeMethod is common or signals.
        # Let's use a global reference or pass signal? 
        # A simple hack for stdout redirect in Qt:
        QApplication.postEvent(self.text_widget, LogEvent(text))

    def flush(self):
        pass

# Custom Event for Thread-Safe Logging
from PyQt6.QtCore import QEvent, QObject
class LogEvent(QEvent):
    TYPE = QEvent.Type(QEvent.registerEventType())
    def __init__(self, text):
        super().__init__(LogEvent.TYPE)
        self.text = text

class ConsoleWidget(QTextEdit):
    def event(self, event):
        if event.type() == LogEvent.TYPE:
            self.moveCursor(self.textCursor().MoveOperation.End)
            self.insertPlainText(event.text)
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
            return True
        return super().event(event)

class VocabookWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vocabook Highlighter")
        self.resize(600, 700)

        self.db = CalibreDB(LIBRARY_PATH)
        self.books = []
        self.book_map = {}
        self.bookmark_map = {}

        self.setup_ui()
        self.load_books()

        # Redirect stdout/stderr
        sys.stdout = StreamRedirect(self.console)
        sys.stderr = StreamRedirect(self.console)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. Book Selection
        group_book = QGroupBox("Select Book")
        layout_book = QVBoxLayout()
        self.combo_book = QComboBox()
        self.combo_book.currentIndexChanged.connect(self.on_book_selected)
        layout_book.addWidget(self.combo_book)
        group_book.setLayout(layout_book)
        main_layout.addWidget(group_book)

        # 2. Bookmarks
        group_bm = QGroupBox("Highlight Range (Bookmarks)")
        layout_bm = QVBoxLayout()
        
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Start After:"))
        self.combo_start = QComboBox()
        row1.addWidget(self.combo_start)
        layout_bm.addLayout(row1)
        
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Stop Before:"))
        self.combo_end = QComboBox()
        row2.addWidget(self.combo_end)
        layout_bm.addLayout(row2)

        group_bm.setLayout(layout_bm)
        main_layout.addWidget(group_bm)

        # 3. Actions
        self.btn_run = QPushButton("Update Highlights")
        self.btn_run.clicked.connect(self.run_process)
        self.btn_run.setFixedHeight(40)
        main_layout.addWidget(self.btn_run)
        
        # Reset Button (Red)
        self.btn_reset = QPushButton("Reset Database & Highlights")
        self.btn_reset.setStyleSheet("background-color: #ffcccc; color: red; font-weight: bold;")
        self.btn_reset.clicked.connect(self.reset_progress)
        self.btn_reset.setFixedHeight(40)
        main_layout.addWidget(self.btn_reset)

        # 4. Anki-style Tools
        group_tools = QGroupBox("Tools")
        layout_tools = QHBoxLayout()
        
        self.btn_browse = QPushButton("Browse Database")
        self.btn_browse.clicked.connect(self.open_browser)
        layout_tools.addWidget(self.btn_browse)
        
        self.btn_stats = QPushButton("View Statistics")
        self.btn_stats.clicked.connect(self.open_stats)
        layout_tools.addWidget(self.btn_stats)
        
        group_tools.setLayout(layout_tools)
        main_layout.addWidget(group_tools)

        # 5. Console
        group_log = QGroupBox("Logs")
        layout_log = QVBoxLayout()
        self.console = ConsoleWidget()
        self.console.setReadOnly(True)
        layout_log.addWidget(self.console)
        group_log.setLayout(layout_log)
        main_layout.addWidget(group_log)

    def open_browser(self):
        from src.browser_window import BrowserWindow
        self.browser_win = BrowserWindow()
        self.browser_win.show()
        
    def open_stats(self):
        from src.stats_window import StatsWindow
        self.stats_win = StatsWindow()
        self.stats_win.show()

    def reset_progress(self):
        book_name = self.combo_book.currentText()
        if not book_name:
            QMessageBox.warning(self, "Warning", "Please select a book to clear highlights from.")
            return

        book_id = self.book_map.get(book_name)
        if not book_id: return

        reply = QMessageBox.question(self, "Confirm Reset", 
                                     "Are you sure you want to RESET ALL PROGRESS?\n\n"
                                     "This will:\n"
                                     "1. Delete all FSRS review history.\n"
                                     "2. Reset all word states to 'New'.\n"
                                     "3. DELETE ALL HIGHLIGHTS for the selected book.\n\n"
                                     "This cannot be undone.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            print("\n--- Resetting Progress ---")
            try:
                # 1. Reset FSRS Database
                from src.fsrs_manager import FSRSManager
                fsrs = FSRSManager()
                fsrs.reset_all_progress()
                
                # 2. Clear Highlights for selected book
                print(f"Removing highlights for Book ID {book_id}...")
                self.db.delete_book_highlights(book_id)
                
                QMessageBox.information(self, "Reset Complete", "All progress has been reset and highlights removed.")
                print("--- Reset Complete ---\n")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reset: {e}")
                print(f"Error during reset: {e}")

    def load_books(self):
        print("Loading books...")
        try:
            raw_books = self.db.get_all_books()
            self.books = sorted(raw_books, key=lambda x: x[1])
            self.combo_book.clear()
            self.book_map = {}
            
            names = []
            for bid, title, _ in self.books:
                name = f"{title} (ID: {bid})"
                self.book_map[name] = bid
                names.append(name)
            
            self.combo_book.addItems(names)
            if names:
                print(f"Loaded {len(names)} books.")
        except Exception as e:
            print(f"Error loading books: {e}")

    def on_book_selected(self):
        name = self.combo_book.currentText()
        if not name or name not in self.book_map: return
        
        book_id = self.book_map[name]
        self.load_bookmarks(book_id)

    def load_bookmarks(self, book_id):
        print(f"Fetching bookmarks for Book ID {book_id}...")
        bookmarks = self.db.get_bookmarks(book_id)
        
        self.bookmark_map = {"Start of Book": None, "End of Book": None}
        display_names = ["Start of Book"]
        
        for bm in bookmarks:
            label = f"{bm['text'][:30]}... (Spine: {bm['spine_index']})"
            key = label
            counter = 1
            while key in self.bookmark_map:
                key = f"{label} ({counter})"
                counter += 1
            
            self.bookmark_map[key] = bm['start_cfi']
            display_names.append(key)
            
        display_names.append("End of Book")
        
        self.combo_start.clear()
        self.combo_start.addItems(display_names)
        self.combo_start.setCurrentIndex(0)
        
        self.combo_end.clear()
        self.combo_end.addItems(display_names)
        self.combo_end.setCurrentIndex(len(display_names)-1)
        
        print(f"Loaded {len(bookmarks)} bookmarks.")

    def run_process(self):
        book_name = self.combo_book.currentText()
        if not book_name:
            QMessageBox.warning(self, "Warning", "Please select a book first.")
            return
            
        book_id = self.book_map[book_name]
        start_key = self.combo_start.currentText()
        end_key = self.combo_end.currentText()
        
        start_cfi = self.bookmark_map.get(start_key)
        end_cfi = self.bookmark_map.get(end_key)
        
        self.btn_run.setEnabled(False)
        self.btn_run.setText("Processing...")
        
        self.worker = WorkerThread(book_id, start_cfi, end_cfi)
        self.worker.finished.connect(self.on_process_finished)
        self.worker.error.connect(self.on_process_error)
        self.worker.start()

    def on_process_finished(self):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("Update Highlights")
        QMessageBox.information(self, "Success", "Highlighting process complete.")
        print("\n--- Done ---")

    def on_process_error(self, err_msg):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("Update Highlights")
        QMessageBox.critical(self, "Error", f"An error occurred:\n{err_msg}")
        print(f"\nERROR: {err_msg}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VocabookWindow()
    window.show()
    sys.exit(app.exec())
