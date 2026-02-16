import sys
from PyQt6.QtWidgets import QApplication
from src.browser_window import BrowserWindow
from src.stats_window import StatsWindow

def verify_windows():
    app = QApplication(sys.argv)
    
    print("Testing Browse Window...")
    try:
        browser = BrowserWindow()
        print("Browse Window created successfully.")
        browser.close()
    except Exception as e:
        print(f"Browse Window Failed: {e}")

    print("Testing Stats Window...")
    try:
        stats = StatsWindow()
        print("Stats Window created successfully.")
        stats.close()
    except Exception as e:
        print(f"Stats Window Failed: {e}")
        
    print("Verification complete.")

if __name__ == "__main__":
    verify_windows()
