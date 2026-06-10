import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QComboBox, QPushButton, 
                             QTextEdit, QGroupBox, QMessageBox, QDoubleSpinBox, QSpinBox, QCheckBox, QFormLayout)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QProcess, QByteArray
import threading
from src.calibre_db import CalibreDB
from src.bulk_highlighter import process_book
from src.epub_injector import EpubInjector
from src.fsrs_manager import FSRSManager
from src.review_sync import ReviewSync
from src.cfi_utils import parse_cfi_to_path
import re
import sqlite3
import json
import os

LIBRARY_PATH = '/Users/karthiktalluri/Calibre Library'

class WorkerThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    log_signal = pyqtSignal(str)

    def __init__(self, book_id, start_spine, end_spine):
        super().__init__()
        self.book_id = book_id
        self.start_spine = start_spine
        self.end_spine = end_spine

    def run(self):
        try:

            process_book(self.book_id, self.start_spine, self.end_spine)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class StreamRedirect:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, text):

        QApplication.postEvent(self.text_widget, LogEvent(text))

    def flush(self):
        pass

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

        self.library_path = LIBRARY_PATH 
        self.db = CalibreDB(self.library_path)
        self.books = []
        self.book_map = {}
        self.bookmark_map = {}
        self.current_book_id = None

        self.setup_ui()
        self.load_books()

        sys.stdout = StreamRedirect(self.console)
        sys.stderr = StreamRedirect(self.console)

    def log(self, text):
        print(text)

    def log_message(self, text):
        self.log(text)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        group_book = QGroupBox("Select Book")
        layout_book = QVBoxLayout()
        self.combo_book = QComboBox()
        self.combo_book.currentIndexChanged.connect(self.on_book_selected)
        layout_book.addWidget(self.combo_book)
        group_book.setLayout(layout_book)
        main_layout.addWidget(group_book)


        history_group = QGroupBox("History Bookmarks (Sync Past Reading)")
        history_layout = QVBoxLayout()
        
        h_start_layout = QHBoxLayout()
        h_start_layout.addWidget(QLabel("Start After:"))
        self.combo_hist_start = QComboBox()
        h_start_layout.addWidget(self.combo_hist_start)
        history_layout.addLayout(h_start_layout)
        
        h_end_layout = QHBoxLayout()
        h_end_layout.addWidget(QLabel("Stop Before:"))
        self.combo_hist_end = QComboBox()
        h_end_layout.addWidget(self.combo_hist_end)
        history_layout.addLayout(h_end_layout)
        
        self.btn_sync = QPushButton("Sync Reviews (Colors -> FSRS)")
        self.btn_sync.clicked.connect(self.run_sync_reviews)
        self.btn_sync.setToolTip("Update FSRS states based on highlight colors in this range.\nYellow=Again, Others=Good.")
        history_layout.addWidget(self.btn_sync)
        
        history_group.setLayout(history_layout)
        main_layout.addWidget(history_group)


        ai_group = QGroupBox("Future Bookmarks (Prepare Next Reading)")
        ai_layout = QVBoxLayout()

        f_start_layout = QHBoxLayout()
        f_start_layout.addWidget(QLabel("Start After:"))
        self.combo_future_start = QComboBox()
        f_start_layout.addWidget(self.combo_future_start)
        ai_layout.addLayout(f_start_layout)
        
        f_end_layout = QHBoxLayout()
        f_end_layout.addWidget(QLabel("Stop Before:"))
        self.combo_future_end = QComboBox()
        f_end_layout.addWidget(self.combo_future_end)
        ai_layout.addLayout(f_end_layout)
        
        settings_layout = QFormLayout()
        
        self.spin_ratio = QDoubleSpinBox()
        self.spin_ratio.setRange(0.001, 0.1)
        self.spin_ratio.setSingleStep(0.005)
        self.spin_ratio.setValue(0.02)
        self.spin_ratio.setDecimals(3)
        settings_layout.addRow("Token Ratio:", self.spin_ratio)
        
        self.btn_calc = QPushButton("Calculate Estimate")
        self.btn_calc.clicked.connect(self.calculate_estimate)
        settings_layout.addRow("", self.btn_calc)
        
        target_row = QHBoxLayout()
        self.check_auto = QCheckBox("Auto")
        self.check_auto.setChecked(True)
        self.check_auto.toggled.connect(self.toggle_word_input)
        target_row.addWidget(self.check_auto)
        
        self.spin_words = QSpinBox()
        self.spin_words.setRange(1, 1000)
        self.spin_words.setValue(10)
        self.spin_words.setEnabled(False)
        target_row.addWidget(self.spin_words)
        settings_layout.addRow("Target Words:", target_row)
        
        self.spin_chunk_size = QSpinBox()
        self.spin_chunk_size.setRange(100, 5000)
        self.spin_chunk_size.setValue(1000)
        settings_layout.addRow("Chunk Size:", self.spin_chunk_size)
        
        self.spin_chunk_overlap = QSpinBox()
        self.spin_chunk_overlap.setRange(0, 1000)
        self.spin_chunk_overlap.setValue(200)
        settings_layout.addRow("Overlap:", self.spin_chunk_overlap)
        
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(10, 72)
        self.spin_font_size.setValue(22)
        self.spin_font_size.setToolTip("Base font size for the EPUB text. Will apply to the whole book.")
        settings_layout.addRow("Font Size (pt):", self.spin_font_size)
        
        ai_layout.addLayout(settings_layout)
        
        self.btn_inject = QPushButton("Inject && Highlight (AI)")
        self.btn_inject.clicked.connect(self.run_ai_injection)
        ai_layout.addWidget(self.btn_inject)
        
        
        ai_group.setLayout(ai_layout)
        main_layout.addWidget(ai_group)
        
        group_tools = QGroupBox("Tools")
        layout_tools = QHBoxLayout()
        
        self.btn_browse = QPushButton("Browse DB")
        self.btn_browse.clicked.connect(self.open_browser)
        layout_tools.addWidget(self.btn_browse)
        
        self.btn_stats = QPushButton("Stats")
        self.btn_stats.clicked.connect(self.open_stats)
        layout_tools.addWidget(self.btn_stats)
        
        self.btn_reset = QPushButton("Reset All")
        self.btn_reset.setStyleSheet("background-color: #ffcccc; color: red;")
        self.btn_reset.clicked.connect(self.reset_progress)
        layout_tools.addWidget(self.btn_reset)
        
        group_tools.setLayout(layout_tools)
        main_layout.addWidget(group_tools)

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

                from src.fsrs_manager import FSRSManager
                fsrs = FSRSManager()
                fsrs.reset_all_progress()
                
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

    def log_message(self, message):
        if hasattr(self, 'console'):
            self.console.append(message)
        print(message)

    def log(self, message):
        self.log_message(message)

    def populate_bookmarks(self):
        book_id = self.current_book_id
        if not book_id: return
        
        self.log(f"Fetching bookmarks for Book ID {book_id}...")
        try:
            conn = sqlite3.connect(os.path.join(self.library_path, 'metadata.db'))
            c = conn.cursor()
            c.execute("SELECT annot_data FROM annotations WHERE book=? AND annot_type='bookmark'", (book_id,))
            rows = c.fetchall()
            conn.close()
            
            bookmarks = []
            for r in rows:
                try:
                    d = json.loads(r[0])
                    if 'pos' in d and 'title' in d:
                        bookmarks.append(d)
                except:
                    continue
            
            if not bookmarks:
                self.log("No bookmarks found. Using default full-book range.")
            else:
                self.log(f"Loaded {len(bookmarks)} real bookmarks.")
            
            self.combo_hist_start.clear()
            self.combo_hist_end.clear()
            self.combo_future_start.clear()
            self.combo_future_end.clear()
            
            self.combo_hist_start.addItem("Start of Book", userData=None)
            self.combo_hist_end.addItem("Start of Book", userData=None)
            self.combo_future_start.addItem("Start of Book", userData=None)
            self.combo_future_end.addItem("Start of Book", userData=None)
            
            for b in bookmarks:
                title = b.get('title', 'Untitled')
                pos = b.get('pos', '???')
                spine_val = "?"
                try:
                     parts = pos.split('/')
                     if len(parts) > 1: spine_val = parts[2]
                except: pass
                
                label = f"{title} (Spine: {spine_val})"
                
                self.combo_hist_start.addItem(label, userData=pos)
                self.combo_hist_end.addItem(label, userData=pos)
                self.combo_future_start.addItem(label, userData=pos)
                self.combo_future_end.addItem(label, userData=pos)
            
            self.combo_hist_start.addItem("End of Book", userData=None)
            self.combo_hist_end.addItem("End of Book", userData=None)
            self.combo_future_start.addItem("End of Book", userData=None)
            self.combo_future_end.addItem("End of Book", userData=None)
            
            last_idx = self.combo_hist_end.count() - 1
            self.combo_hist_end.setCurrentIndex(last_idx)
            self.combo_future_end.setCurrentIndex(last_idx)
                
        except Exception as e:
            self.log(f"Error loading bookmarks: {e}")
                
        except Exception as e:
            self.log(f"Error loading bookmarks: {e}")

    def on_book_selected(self):
        text = self.combo_book.currentText()
        if not text: return
        match = re.search(r'\(ID: (\d+)\)', text)
        if match:
            bid = match.group(1)
            self.current_book_id = bid
            self.populate_bookmarks()

    def get_range_from_combos(self, combo_start, combo_end):
        """Helper to get start/end CFI and spine from combo boxes."""
        start_cfi = combo_start.currentData()
        end_cfi = combo_end.currentData()
        start_text = combo_start.currentText()
        end_text = combo_end.currentText()
        
        start_spine = 0
        end_spine = 100000
        
        if start_text == "End of Book":
            start_spine = 100000
        
        if end_text == "Start of Book":
            end_spine = 0

        if start_cfi:
            parsed = parse_cfi_to_path(start_cfi)
            if parsed:
                 start_spine = (parsed[0] // 2) - 1
                 start_spine = max(0, start_spine)
                 
        if end_cfi:
            parsed = parse_cfi_to_path(end_cfi)
            if parsed:
                 end_spine = (parsed[0] // 2) - 1
                 end_spine = max(0, end_spine)
                 
        return start_spine, end_spine, start_cfi, end_cfi

    def run_process(self):
        book_name = self.combo_book.currentText()
        if not book_name:
            QMessageBox.warning(self, "Warning", "Please select a book first.")
            return
            
        book_id = self.book_map[book_name]
        start_key = self.combo_start.currentText()
        end_key = self.combo_end.currentText()
        
        bm_start = self.bookmark_map.get(start_key)
        bm_end = self.bookmark_map.get(end_key)
        
        start_spine = bm_start.get('spine', 0) if isinstance(bm_start, dict) else 0
        end_spine = bm_end.get('spine', 999999) if isinstance(bm_end, dict) else 999999
        
        self.btn_run.setEnabled(False)
        self.btn_run.setText("Processing...")
        
        self.worker = WorkerThread(book_id, start_spine, end_spine)
        self.worker.finished.connect(self.on_process_finished)
        self.worker.error.connect(self.on_process_error)
        self.worker.start()

    def toggle_word_input(self, checked):
        self.spin_words.setEnabled(not checked)

    def calculate_estimate(self):
        selected_items = self.combo_book.currentText()
        if not selected_items:
            self.log_message("Please select a book first.")
            return

        book_id = self.book_map.get(selected_items)
        if not book_id: return
        
        start_key = self.combo_start.currentText()
        end_key = self.combo_end.currentText()
        

        
        bm_start = self.bookmark_map.get(start_key)
        bm_end = self.bookmark_map.get(end_key)
        
        start_spine = 0
        end_spine = 999999
        
        if bm_start and isinstance(bm_start, dict):
             start_spine = bm_start.get('spine', 0)
        
        if bm_end and isinstance(bm_end, dict):
             end_spine = bm_end.get('spine', 999999)

        self.btn_calc.setText("Scanning...")
        self.btn_calc.setEnabled(False)
        
        self.scan_process = QProcess()
        self.scan_process.readyReadStandardOutput.connect(self.handle_scan_output)
        self.scan_process.finished.connect(self.scan_finished)
        
        script = "src/scan_helper.py"
        program = sys.executable 
        args = [script, "--book_id", str(book_id), 
                "--library_path", LIBRARY_PATH,
                "--start_spine", str(start_spine),
                "--end_spine", str(end_spine)]
                
        self.log_message(f"Running scan with args: {args}")
        self.scan_process.start(program, args)
        
    def handle_scan_output(self):
        data = self.scan_process.readAllStandardOutput()
        text = str(data, encoding='utf-8').strip()
        lines = text.split('\n')
        for line in lines:
            if line.isdigit():
                self.scanned_token_count = int(line)

    def scan_finished(self):
        self.btn_calc.setEnabled(True)
        self.btn_calc.setText("Calculate Estimate")
        
        count = getattr(self, 'scanned_token_count', 0)
        
        if count > 0:
            ratio = self.spin_ratio.value()
            est_words = int(count * ratio)
            est_words = max(1, est_words)
            
            self.check_auto.setChecked(False)
            self.spin_words.setValue(est_words)
            
            self.log_message(f"Scanned {count} tokens (in selected range). Estimated Target: {est_words} words.")
        else:
            self.log_message("Scan finished but returned 0 tokens. Check selection.")
            
        self.scanned_token_count = 0 

    def on_scan_complete(self, token_count):
        pass

    def run_sync_reviews(self):
        book_id = self.current_book_id
        if not book_id:
            self.log("Please select a book first.")
            return
            
        try:
            bid = int(book_id)
            self.log(f"Starting Review Sync for Book {bid}...")
            
            start_spine, end_spine, start_cfi, end_cfi = self.get_range_from_combos(self.combo_hist_start, self.combo_hist_end)
            
            syncer = ReviewSync(self.library_path, "vocabook.db")
            syncer.sync_book_reviews(bid, start_spine, end_spine, start_cfi, end_cfi)
            
            self.log("Sync Complete! Check console for details.")
            
        except ValueError:
            self.log("Invalid Book ID.")
        except Exception as e:
            self.log(f"Error during sync: {e}")

    def calculate_estimate(self):
        selected_items = self.combo_book.currentText()
        if not selected_items:
            self.log_message("Please select a book first.")
            return

        book_id = self.book_map.get(selected_items)
        if not book_id: return
        
        start_key = self.combo_future_start.currentText()
        end_key = self.combo_future_end.currentText()
        
        start_spine, end_spine, start_cfi, end_cfi = self.get_range_from_combos(self.combo_future_start, self.combo_future_end)

        self.btn_calc.setText("Scanning...")
        self.btn_calc.setEnabled(False)
        
        self.scan_process = QProcess()
        self.scan_process.readyReadStandardOutput.connect(self.handle_scan_output)
        self.scan_process.finished.connect(self.scan_finished)
        
        script = "src/scan_helper.py"
        program = sys.executable 
        args = [script, "--book_id", str(book_id), 
                "--library_path", self.library_path,
                "--start_spine", str(start_spine),
                "--end_spine", str(end_spine)]
                
        self.log_message(f"Running scan with args: {args}")
        self.scan_process.start(program, args)
        
    def run_ai_injection(self):
        selected_items = self.combo_book.currentText()
        if not selected_items:
            self.log_message("Please select a book first.")
            return

        book_id = self.book_map.get(selected_items)
        if not book_id: return
        
        if self.check_auto.isChecked():
            num_words = 0
        else:
            num_words = self.spin_words.value()
            
        ratio = self.spin_ratio.value()
        
        start_spine, end_spine, start_cfi, end_cfi = self.get_range_from_combos(self.combo_future_start, self.combo_future_end)
        
        chunk_size = self.spin_chunk_size.value()
        chunk_overlap = self.spin_chunk_overlap.value()
        
        font_size = self.spin_font_size.value()
        
        self.btn_inject.setEnabled(False)
        self.btn_inject.setText("Running AI...")
        
        self.ai_worker = AIWorker(book_id, num_words, ratio, start_spine, end_spine, start_cfi, end_cfi, chunk_size, chunk_overlap, font_size)
        self.ai_worker.log_signal.connect(self.console_log)
        self.ai_worker.finished_signal.connect(self.on_ai_finished)
        self.ai_worker.start()

    def on_ai_finished(self):
        self.btn_inject.setEnabled(True)
        self.btn_inject.setText("Inject && Highlight (AI)")
        QMessageBox.information(self, "Success", "AI Injection & Highlighting Complete.")
        
    def console_log(self, msg):
        print(msg)

class AIWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, book_id, num_words, ratio, start_spine, end_spine, start_cfi=None, end_cfi=None, chunk_size=1000, chunk_overlap=200, font_size=22):
        super().__init__()
        self.book_id = book_id
        self.num_words = num_words
        self.ratio = ratio
        self.start_spine = start_spine
        self.end_spine = end_spine
        self.start_cfi = start_cfi
        self.end_cfi = end_cfi
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.font_size = font_size
        self.library_path = '/Users/karthiktalluri/Calibre Library'
        
    def run(self):
        try:
            self.log_signal.emit(f"Starting AI Injection for Book {self.book_id}...")
            

            final_num_words = self.num_words
            
            if final_num_words == 0:
                self.log_signal.emit(f"Auto-calculating words (Ratio: {self.ratio})...")
                script = "src/scan_helper.py"
                args = [sys.executable, script, 
                        "--book_id", str(self.book_id), 
                        "--library_path", self.library_path,
                        "--start_spine", str(self.start_spine),
                        "--end_spine", str(self.end_spine)]
                        
                import subprocess
                try:
                    output = subprocess.check_output(args, text=True).strip()
                    lines = output.split('\n')
                    token_count = 0
                    for line in lines:
                        if line.isdigit():
                            token_count = int(line)
                            
                    self.log_signal.emit(f"Token Count (Range): {token_count}")
                    
                    est_words = int(token_count * self.ratio)
                    final_num_words = max(1, est_words)
                    self.log_signal.emit(f"Calculated Target Words: {final_num_words}")
                    
                except subprocess.CalledProcessError as e:
                    self.log_signal.emit(f"Scan failed: {e}")
                    final_num_words = 1
            
            self.log_signal.emit(f"Injecting {final_num_words} words (Chunk: {self.chunk_size}, Overlap: {self.chunk_overlap})...")
            

            injector = EpubInjector(self.library_path) 
            
            result = injector.inject_auto(self.book_id, 
                                          manual_num_words=final_num_words,
                                          chunk_size=self.chunk_size,
                                          chunk_overlap=self.chunk_overlap,
                                          start_spine=self.start_spine,
                                          end_spine=self.end_spine,
                                          start_cfi=self.start_cfi,
                                          end_cfi=self.end_cfi,
                                          font_size=self.font_size)
            
            if result:
                self.log_signal.emit(f"AI Stage Complete. Injected {result['count']} words.")
                if result['injected']:
                    self.log_signal.emit(f"Injected: {', '.join(result['injected'])}")
                
                missing = result.get('missing', [])
                if missing:
                    self.log_signal.emit(f"WARNING: Could not find suitable positions for {len(missing)} words:")
                    self.log_signal.emit(f"Missing: {', '.join(missing)}")
                    self.log_signal.emit("Proceeding with highlighting...")
            else:
                self.log_signal.emit("AI Stage Failed or No words injected.")
                

            self.log_signal.emit("Starting Standard Highlighting (Stage 2 - AI Words Only)...")
            
            injected_list = result.get('injected', []) if result else []
            
            if injected_list:
                process_book(self.book_id, self.start_spine, self.end_spine, whitelist=injected_list, start_cfi=self.start_cfi, end_cfi=self.end_cfi)
                self.log_signal.emit("Highlighting process finished.")
            else:
                self.log_signal.emit("Skipping highlighting (No words injected).")
            
        except Exception as e:
            self.log_signal.emit(f"Error: {e}")
        finally:
            self.finished_signal.emit()

    def log_message(self, msg):
        print(msg)

    def on_process_finished(self):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("Highlight Existing (Non-AI)")
        QMessageBox.information(self, "Success", "Highlighting process complete.")
        print("\n--- Done ---")

    def on_process_error(self, err_msg):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("Highlight Existing (Non-AI)")
        QMessageBox.critical(self, "Error", f"An error occurred:\n{err_msg}")
        print(f"\nERROR: {err_msg}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VocabookWindow()
    window.show()
    sys.exit(app.exec())
