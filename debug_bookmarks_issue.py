import sqlite3
import json
import os

LIBRARY_PATH = '/Users/karthiktalluri/Calibre Library'
DB_PATH = os.path.join(LIBRARY_PATH, 'metadata.db')
BOOK_ID = 26

def inspect():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"--- Inspecting Annotations for Book {BOOK_ID} ---")
    
    # Get all types
    cursor.execute("SELECT annot_type, annot_data FROM annotations WHERE book=?", (BOOK_ID,))
    rows = cursor.fetchall()
    
    if not rows:
        print("No annotations found at all for this book.")
        
    for idx, (atype, data_json) in enumerate(rows):
        print(f"\n[Entry {idx}] Type: {atype}")
        try:
            data = json.loads(data_json)
            print(json.dumps(data, indent=2))
        except:
            print(f"Raw Data: {data_json}")

    conn.close()

if __name__ == "__main__":
    inspect()
