import sqlite3
import os

LIBRARY_PATH = '/Users/karthiktalluri/Calibre Library'
DB_PATH = os.path.join(LIBRARY_PATH, 'metadata.db')

def check_integrity():
    print(f"Checking database: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("Database file not found!")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        print("Running PRAGMA integrity_check...")
        cursor.execute("PRAGMA integrity_check;")
        results = cursor.fetchall()
        for row in results:
            print(row[0])
        conn.close()
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    check_integrity()
