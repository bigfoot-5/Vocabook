import sqlite3
import json
import os

LIBRARY_PATH = '/Users/karthiktalluri/Calibre Library'
DB_PATH = os.path.join(LIBRARY_PATH, 'metadata.db')
BOOK_ID = 3

def inspect_annotations():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"--- Annotations for Book ID {BOOK_ID} ---")
    
    try:
        cursor.execute("SELECT id, annot_data, searchable_text FROM annotations WHERE book=?", (BOOK_ID,))
        rows = cursor.fetchall()
        
        if not rows:
            print("No annotations found.")
        
        for row in rows:
            annot_id, data_json, text = row
            print(f"\n[ID: {annot_id}] Text: '{text}'")
            try:
                data = json.loads(data_json)
                print(json.dumps(data, indent=2))
            except json.JSONDecodeError:
                print("Invalid JSON data")
                print(data_json)
                
    except Exception as e:
        print(f"Error reading DB: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_annotations()
