import sqlite3
import json

LIBRARY_PATH = '/Users/karthiktalluri/Calibre Library'
DB_PATH = LIBRARY_PATH + '/metadata.db'
BOOK_ID = 22

def inspect_annotations():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # List columns in annotations table just in case
    cursor.execute("PRAGMA table_info(annotations)")
    columns = cursor.fetchall()
    print("Columns:", [c[1] for c in columns])

    # Fetch annotations for book
    cursor.execute("SELECT annot_id, annot_data, searchable_text FROM annotations WHERE book=?", (BOOK_ID,))
    rows = cursor.fetchall()
    
    print(f"\nFound {len(rows)} annotations:")
    for row in rows:
        annot_id, data_json, text = row
        try:
            data = json.loads(data_json)
            print(f"\nID: {annot_id}")
            print(f"Text: {text}")
            print(f"Data: {json.dumps(data, indent=2)}")
        except:
            print(f"Raw Data: {data_json}")

    conn.close()

if __name__ == "__main__":
    inspect_annotations()
