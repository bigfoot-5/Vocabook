import sqlite3
import os

LIBRARY_PATH = '/Users/karthiktalluri/Calibre Library'
# DB_PATH = os.path.join(LIBRARY_PATH, 'metadata.db')
# Testing on new DB first
DB_PATH = 'metadata_new.db'

def force_delete_highlights(book_id):
    print(f"Force deleting highlights for Book ID {book_id}...")
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check before
        cursor.execute("SELECT count(*) FROM annotations WHERE book=? AND annot_type='highlight'", (book_id,))
        before = cursor.fetchone()[0]
        print(f"Highlights before: {before}")
        
        # Delete
        cursor.execute("DELETE FROM annotations WHERE book=? AND annot_type='highlight'", (book_id,))
        count = cursor.rowcount
        print(f"Rows deleted: {count}")
        
        conn.commit()
        
        # Check after
        cursor.execute("SELECT count(*) FROM annotations WHERE book=? AND annot_type='highlight'", (book_id,))
        after = cursor.fetchone()[0]
        print(f"Highlights after: {after}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    force_delete_highlights(26)
