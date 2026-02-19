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

    def add_annotation(self, book_id, text, cfi_start, cfi_end, spine_index, spine_name, notes=None, color="green"):
        uuid_str = str(uuid.uuid4())
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        annot_data = {
            "type": "highlight",
            "timestamp": timestamp,
            "uuid": uuid_str,
            "highlighted_text": text,
            "start_cfi": cfi_start, 
            "end_cfi": cfi_end,
            "style": {"type": "builtin", "kind": "color", "which": color},
            "spine_name": spine_name,
            "spine_index": ((spine_index // 2) - 1) 
        }
        
        if notes:
            annot_data["notes"] = notes
        
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

    def get_existing_highlights(self, book_id):
        """
        Returns a set of start_cfi strings for existing highlights of a book.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        existing = set()
        try:
            cursor.execute("SELECT annot_data FROM annotations WHERE book=? AND annot_type='highlight'", (book_id,))
            rows = cursor.fetchall()
            for row in rows:
                try:
                    data = json.loads(row[0])
                    if 'start_cfi' in data:
                        existing.add(data['start_cfi'])
                except:
                    continue
        except Exception as e:
            print(f"Error fetching existing highlights: {e}")
        finally:
            conn.close()
        return existing

    def fetch_book_highlights(self, book_id):
        """
        Fetches all highlight annotations for a book.
        Returns a list of dicts (the parsed annot_data).
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        highlights = []
        try:
            cursor.execute("SELECT annot_data, timestamp FROM annotations WHERE book=? AND annot_type='highlight'", (book_id,))
            rows = cursor.fetchall()
            for row in rows:
                try:
                    data = json.loads(row[0])
                    # Inject timestamp from DB if not in data (though it usually is)
                    data['db_timestamp'] = row[1]
                    highlights.append(data)
                except:
                    continue
        except Exception as e:
            print(f"Error fetching highlights: {e}")
        finally:
            conn.close()
        return highlights

    def get_highlights_with_metadata(self, book_id):
        """
        Returns list of dicts: {'text': str, 'color': str, 'timestamp': str, 'cfi': str}
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        results = []
        try:
            cursor.execute("SELECT annot_data FROM annotations WHERE book=? AND annot_type='highlight'", (book_id,))
            rows = cursor.fetchall()
            for row in rows:
                try:
                    data = json.loads(row[0])
                    # Extract Data
                    text = data.get('highlighted_text', data.get('text', ''))
                    # Color is nested: style -> which (e.g. "green", "blue")
                    style = data.get('style', {})
                    color = style.get('which', 'unknown')
                    timestamp = data.get('timestamp')
                    cfi = data.get('start_cfi')
                    
                    if text:
                        results.append({
                            'text': text,
                            'color': color,
                            'timestamp': timestamp,
                            'cfi': cfi
                        })
                except:
                    continue
        except Exception as e:
            print(f"Error fetching highlight metadata: {e}")
        finally:
            conn.close()
        return results

    def get_all_books(self):
        """
        Returns a list of tuples: (id, title, author_sort)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, title, author_sort FROM books ORDER BY title")
            return cursor.fetchall()
        except Exception as e:
            print(f"Error fetching books: {e}")
            return []
        finally:
            conn.close()

    def get_bookmarks(self, book_id):
        """
        Returns a list of bookmark dicts:
        [{'uuid': ..., 'text': 'Note/Text', 'start_cfi': ..., 'spine_index': ...}, ...]
        Sorted by spine_index then start_cfi.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        bookmarks = []
        try:
            cursor.execute("SELECT annot_data FROM annotations WHERE book=? AND annot_type='bookmark'", (book_id,))
            rows = cursor.fetchall()
            
            for row in rows:
                try:
                    data = json.loads(row[0])
                    
                    # Schema 1: Highlight-style
                    if 'start_cfi' in data:
                        bookmarks.append({
                            'uuid': data.get('uuid', ''),
                            'text': data.get('notes', data.get('text', 'Bookmark')),
                            'start_cfi': data.get('start_cfi'),
                            'spine_index': data.get('spine_index', 0),
                            'timestamp': data.get('timestamp')
                        })
                    # Schema 2: Bookmark-style
                    elif 'pos' in data:
                        cfi = data.get('pos')
                        # Extract spine index from CFI if possible
                        # cfi like "epubcfi(/18/2/...)"
                        # spine index roughly (18 - 2) / 2 ? Or just parse 18.
                        # We use a helper or just 0 if unknown.
                        spine_idx = 0
                        clean_cfi = cfi.replace("epubcfi(", "").replace(")", "")
                        parts = clean_cfi.split('/')
                        if len(parts) > 1 and parts[1].isdigit():
                             # /2 is root, /4 is spine 0? 
                             # Actually usually: /2/spine_idx_step...
                             # If it is /18 => (18/2) - 1 = 8? 
                             # Let's just use the raw int for sorting.
                             spine_idx = int(parts[1])
                        
                        bookmarks.append({
                            'uuid': data.get('uuid', ''),
                            'text': data.get('title', 'Bookmark'),
                            'start_cfi': cfi, # Use 'pos' as start_cfi
                            'spine_index': spine_idx,
                            'timestamp': data.get('timestamp')
                        })
                        
                except Exception as loop_e:
                    print(f"Skipping bad bookmark row: {loop_e}")
                    continue
                    
            # Sort by spine_index, then start_cfi
            bookmarks.sort(key=lambda x: (x['spine_index'], x['start_cfi']))
            
        except Exception as e:
            print(f"Error fetching bookmarks: {e}")
        finally:
            conn.close()
            
        return bookmarks

    def delete_book_highlights(self, book_id):
        """
        Deletes ALL highlights for a specific book.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM annotations WHERE book=? AND annot_type='highlight'", (book_id,))
            deleted_count = cursor.rowcount
            conn.commit()
            print(f"Deleted {deleted_count} highlights for book {book_id}.")
            return deleted_count
        except Exception as e:
            print(f"Error deleting highlights: {e}")
            return 0
        finally:
            conn.close()
