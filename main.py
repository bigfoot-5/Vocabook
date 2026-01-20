import os
import warnings
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub

from src.calibre_db import CalibreDB
from src.epub_utils import EpubManager
from src.cfi_generator import calculate_cfi

# Suppress warnings
warnings.filterwarnings('ignore')

# Configuration
LIBRARY_PATH = '/Users/karthiktalluri/Calibre Library'
BOOK_ID = 13
TARGET_TEXT = "Cataclysm"

def main():
    print(f"Initializing Calibre DB at {LIBRARY_PATH}")
    db = CalibreDB(LIBRARY_PATH)
    
    book_dir = db.get_book_path(BOOK_ID)
    if not book_dir:
        print(f"Book data for ID {BOOK_ID} not found in database.")
        return
        
    print(f"Located book directory: {book_dir}")
    
    epub_path = EpubManager.find_epub_file(book_dir)
    if not epub_path:
        print("EPUB file not found in book directory.")
        return
        
    print(f"Reading EPUB: {epub_path}")
    book = EpubManager.read_book(epub_path)
    if not book:
        return

    found = False
    for i, (item_id, linear) in enumerate(book.spine):
        item = book.get_item_with_id(item_id)
        if not item: continue
        
        if isinstance(item, ebooklib.epub.EpubHtml):
            soup = BeautifulSoup(item.content, 'html.parser')
            
            if TARGET_TEXT in soup.get_text():
                print(f"Found '{TARGET_TEXT}' in {item.file_name} (Spine Index: {i})")
                
                # Calculate CFI
                path_str, _, offsets = calculate_cfi(soup, TARGET_TEXT)
                
                if path_str is not None:
                    spine_cfi = (i + 1) * 2
                    
                    full_start_cfi = f"/{spine_cfi}{path_str}:{offsets[0]}"
                    full_end_cfi = f"/{spine_cfi}{path_str}:{offsets[1]}"
                    
                    print(f"Generated CFI: {full_start_cfi}")
                    
                    # Add to DB
                    # Note: We strip the spine_cfi prefix for the DB storage as learned from debugging
                    db.add_annotation(
                        BOOK_ID, 
                        TARGET_TEXT, 
                        full_start_cfi.replace(f"/{spine_cfi}", ""), 
                        full_end_cfi.replace(f"/{spine_cfi}", ""),
                        spine_cfi, 
                        item.file_name
                    )
                    found = True
                    break
    
    if found:
        print("Done! Annotation added. Please restart Calibre to view.")
    else:
        print(f"Text '{TARGET_TEXT}' not found in the book.")

if __name__ == "__main__":
    main()
