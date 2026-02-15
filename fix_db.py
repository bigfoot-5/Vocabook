import sqlite3
import os

LIBRARY_PATH = '/Users/karthiktalluri/Calibre Library'
DB_PATH = os.path.join(LIBRARY_PATH, 'metadata.db')

def attempt_vacuum():
    print(f"Vacuuming database: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        # conn.execute("VACUUM;")
        # print("VACUUM successful.")
        
        # Taking a safer approach: dump and reload? 
        # Or just try reading everything first?
        # Let's try simple VACUUM first.
        conn.execute("VACUUM;")
        conn.close()
        print("VACUUM finished successfully.")
    except Exception as e:
        print(f"VACUUM FAILED: {e}")

if __name__ == "__main__":
    attempt_vacuum()
