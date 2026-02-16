import sqlite3
import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

DB_PATH = 'vocabook.db'

class StatsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FSRS Statistics")
        self.resize(800, 600)
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Tab 1: Counts
        self.fig_counts = Figure()
        self.canvas_counts = FigureCanvas(self.fig_counts)
        self.tabs.addTab(self.canvas_counts, "Card Counts")
        
        # Tab 2: Future Due
        self.fig_due = Figure()
        self.canvas_due = FigureCanvas(self.fig_due)
        self.tabs.addTab(self.canvas_due, "Future Due")
        
        # Tab 3: Review Intervals
        self.fig_intervals = Figure()
        self.canvas_intervals = FigureCanvas(self.fig_intervals)
        self.tabs.addTab(self.canvas_intervals, "Review Intervals")

    def load_data(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. State Counts
        cursor.execute("SELECT state, COUNT(*) FROM words GROUP BY state")
        state_counts = {0:0, 1:0, 2:0, 3:0}
        for state, count in cursor.fetchall():
            state_counts[state] = count
            
        self.plot_counts(state_counts)
        
        # 2. Future Due
        cursor.execute("SELECT due FROM words WHERE due IS NOT NULL")
        due_rows = cursor.fetchall()
        self.plot_due(due_rows)
        
        # 3. Intervals
        cursor.execute("SELECT scheduled_days FROM words WHERE scheduled_days > 0")
        intervals = [r[0] for r in cursor.fetchall()]
        self.plot_intervals(intervals)
        
        conn.close()

    def plot_counts(self, counts):
        self.fig_counts.clear()
        ax = self.fig_counts.add_subplot(111)
        
        labels = ['New', 'Learning', 'Review', 'Relearning']
        sizes = [counts.get(0,0), counts.get(1,0), counts.get(2,0), counts.get(3,0)]
        colors = ['#3399ff', '#ff3333', '#33cc33', '#ff9933'] # Blue, Red, Green, Orange
        
        # Filter out zero slices to avoid clutter
        final_labels = []
        final_sizes = []
        final_colors = []
        for l, s, c in zip(labels, sizes, colors):
            if s > 0:
                final_labels.append(f"{l} ({s})")
                final_sizes.append(s)
                final_colors.append(c)
                
        if not final_sizes:
            ax.text(0.5, 0.5, "No Data", ha='center')
        else:
            ax.pie(final_sizes, labels=final_labels, colors=final_colors, autopct='%1.1f%%')
            ax.set_title("Card Distribution by State")
            
        self.canvas_counts.draw()

    def plot_due(self, due_rows):
        self.fig_due.clear()
        ax = self.fig_due.add_subplot(111)
        
        # Aggregate by day
        today = datetime.datetime.now(datetime.timezone.utc).date()
        future_reviews = {}
        
        for (iso_str,) in due_rows:
            try:
                dt = datetime.datetime.fromisoformat(iso_str)
                # Ensure UTC awareness if missing (though DB stores ISO)
                if not dt.tzinfo:
                   dt = dt.replace(tzinfo=datetime.timezone.utc)
                
                date_val = dt.date()
                if date_val < today:
                    key = "Overdue"
                else:
                    days_diff = (date_val - today).days
                    key = days_diff # 0 = Today, 1 = Tomorrow...
                    
                future_reviews[key] = future_reviews.get(key, 0) + 1
            except: pass
            
        # Prepare Data for plotting
        # Plot Overdue + Next 30 days
        x = ['Overdue'] + [str(i) for i in range(31)]
        y = [future_reviews.get("Overdue", 0)] + [future_reviews.get(i, 0) for i in range(31)]
        
        ax.bar(x, y, color='skyblue')
        ax.set_title("Future Reviews")
        ax.set_xlabel("Days from Today")
        ax.set_ylabel("Card Count")
        
        # Rotate x labels if crowded
        
        self.canvas_due.draw()

    def plot_intervals(self, intervals):
        self.fig_intervals.clear()
        ax = self.fig_intervals.add_subplot(111)
        
        if not intervals:
            ax.text(0.5, 0.5, "No Review Intervals Data", ha='center')
        else:
            ax.hist(intervals, bins=20, color='purple', alpha=0.7)
            ax.set_title("Scheduled Intervals (Days)")
            ax.set_xlabel("Days")
            ax.set_ylabel("Frequency")
            
        self.canvas_intervals.draw()
