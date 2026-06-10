import re
from src.fsrs_manager import FSRSManager
from src.calibre_db import CalibreDB
from datetime import datetime
import datetime as dt_module

class ReviewSync:
    def __init__(self, library_path, db_path='vocabook.db'):
        self.calibre_db = CalibreDB(library_path)
        self.fsrs = FSRSManager(db_path)
        
        
    def sync_book_reviews(self, book_id, start_spine=0, end_spine=float('inf'), start_cfi=None, end_cfi=None):
        """
        Scans highlights in the book within the specified range.
        Identifies words based on the 'notes' field (format: "Word: Definition").
        Updates FSRS state based on highlight color.
        
        Color Mapping:
        - yellow: Again (1) - "I forgot"
        - green: Good (3) - "I remembered" (Default)
        - blue: Easy (4)
        - red: Hard (2)
        """
        print(f"Syncing reviews for Book ID {book_id}...")
        print(f"Range: Spine {start_spine}-{end_spine}")
        
        highlights = self.calibre_db.fetch_book_highlights(book_id)
        
        if not highlights:
            print("No highlights found.")
            return

        print(f"Found {len(highlights)} highlights. Filtering for range...")
        
        processed_count = 0
        from src.cfi_utils import is_element_in_range
        
        for h in highlights:

            h_cfi = h.get('start_cfi')
            h_spine = h.get('spine_index', -1)
            h_notes = h.get('notes', '')
            
            print(f"[DEBUG] Highlight: Spine={h_spine}, CFI={h_cfi}, Notes='{h_notes}'")

            if not h_cfi: 
                print(f"[DEBUG] -> Skipped: No start_cfi")
                continue
            
            if h_spine != -1:

                if h_spine < start_spine or h_spine > end_spine:
                    print(f"[DEBUG] -> Skipped: Spine {h_spine} outside {start_spine}-{end_spine}")
                    continue
            else:
                print(f"[DEBUG] -> Warning: spine_index is -1 (missing from DB data)")
                    

            in_range = True
            h_path = extract_numeric_path(h_cfi)
            
            if h_spine == start_spine and start_cfi:
                s_path = extract_numeric_path(start_cfi)

                
                effective_s_path = s_path
                if len(s_path) > len(h_path) and s_path[0] != h_path[0]:

                     effective_s_path = s_path[1:]
                
                if h_path < effective_s_path:
                    print(f"[DEBUG] -> Skipped: Below Start CFI. H={h_path}, Start={effective_s_path}")
                    in_range = False
            
            if in_range and h_spine == end_spine and end_cfi:
                e_path = extract_numeric_path(end_cfi)
                effective_e_path = e_path
                if len(e_path) > len(h_path) and e_path[0] != h_path[0]:

                     effective_e_path = e_path[1:]
                     
                if h_path > effective_e_path:
                    print(f"[DEBUG] -> Skipped: Above End CFI. H={h_path}, End={effective_e_path}")
                    in_range = False

            if not in_range:
                continue


            notes = h.get('notes', '')
            if not notes:
                continue
                

            parts = notes.split(':', 1)
            if not parts:
                continue
                
            word_candidate = parts[0]

            word_clean = re.sub(r'<[^>]+>', '', word_candidate).strip()
            
            if not word_clean:
                continue
                

            style = h.get('style', {})
            color = style.get('which', 'green').lower() # Default to green if not specified
            

            
            rating = 3 # Default to Good
            
            if color == 'yellow':
                rating = 1 # Again (Forgot)
            else:
                rating = 3 # Good (Remembered - even if Red/Blue/Green)
                

            timestamp_str = h_cfi # Wait this is wrong variable
            timestamp_str = h.get('db_timestamp') or h.get('timestamp')
            
            review_time = None
            if timestamp_str:

                if isinstance(timestamp_str, (int, float)):
                     review_time = datetime.fromtimestamp(timestamp_str, dt_module.timezone.utc)
                else:
                    try:
                        review_time = datetime.fromisoformat(timestamp_str)
                    except:
                        pass
            
            if not review_time:
                review_time = datetime.now(dt_module.timezone.utc)


            self.fsrs.process_review(word_clean, rating, review_time)
            processed_count += 1
            
        print(f"Sync complete. Processed {processed_count} highlights.")

if __name__ == "__main__":
    pass
