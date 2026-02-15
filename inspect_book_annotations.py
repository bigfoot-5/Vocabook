import sqlite3
import os
import json

LIBRARY_PATH = '/Users/karthiktalluri/Calibre Library'
DB_PATH = os.path.join(LIBRARY_PATH, 'metadata.db')

def inspect_annotations(book_id):
    print(f"Inspecting annotations for Book ID {book_id}...")
    if not os.path.exists(DB_PATH):
        print("Database file not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Check count of all annotations for this book
        cursor.execute("SELECT count(*) FROM annotations WHERE book=?", (book_id,))
        count = cursor.fetchone()[0]
        print(f"Total annotations for book {book_id}: {count}")
        
        # Check types
        cursor.execute("SELECT annot_type, count(*) FROM annotations WHERE book=? GROUP BY annot_type", (book_id,))
        types = cursor.fetchall()
        print("Count by Type:")
        for t in types:
            print(f"  {t[0]}: {t[1]}")
            
        # Dump a few to see structure
        print("\nSample Highlight Data:")
        cursor.execute("SELECT annot_data FROM annotations WHERE book=? AND annot_type='highlight' LIMIT 3", (book_id,))
        rows = cursor.fetchall()
        for row in rows:
            print(json.dumps(json.loads(row[0]), indent=2))
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # The user mentioned Book ID 26 in the logs
    inspect_annotations(26)
