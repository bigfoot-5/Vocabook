import sqlite3
import os
import uuid
import datetime
import json

class CalibreDB:
    def __init__(self, library_path):
        self.library_path = library_path
        self.db_path = os.path.join(library_path, 'metadata.db')

    def get_book_path(self, book_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        query = "SELECT path FROM books WHERE id=?"
        cursor.execute(query, (book_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return os.path.join(self.library_path, result[0])
        return None

    def add_annotation(self, book_id, text, cfi_start, cfi_end, spine_index, spine_name):
        uuid_str = str(uuid.uuid4())
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        annot_data = {
            "type": "highlight",
            "timestamp": timestamp,
            "uuid": uuid_str,
            "highlighted_text": text,
            "start_cfi": cfi_start, 
            "end_cfi": cfi_end,
            "style": {"type": "builtin", "kind": "color", "which": "green"},
            "spine_name": spine_name,
            "spine_index": ((spine_index // 2) - 1) 
        }
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO annotations 
                (book, format, user_type, user, timestamp, annot_id, annot_type, annot_data, searchable_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                book_id,
                'EPUB',
                'local', 
                'viewer',
                datetime.datetime.now().timestamp(),
                uuid_str,
                'highlight',
                json.dumps(annot_data),
                text
            ))
            conn.commit()
            print(f"Successfully added annotation for '{text}'")
        except Exception as e:
            print(f"Database error: {e}")
        finally:
            conn.close()

    def get_start_annotation(self, book_id, note_text="Start Here"):
        """
        Finds the first annotation that contains the specific note text.
        Returns (spine_index, start_cfi) or (None, None).
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # We need to fetch all highlights and check 'notes' field in JSON
        cursor.execute("SELECT annot_data FROM annotations WHERE book=? AND annot_type='highlight'", (book_id,))
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            try:
                data = json.loads(row[0])
                if data.get('notes') == note_text:
                    # Found it!
                    return data.get('spine_index'), data.get('start_cfi')
            except:
                continue
                
        return None, None
