import zipfile
import sys
import os
from src.calibre_db import CalibreDB
from src.epub_utils import EpubManager

LIBRARY_PATH = '/Users/karthiktalluri/Calibre Library'
BOOK_ID = 3

def list_epub_files():
    db = CalibreDB(LIBRARY_PATH)
    book_dir = db.get_book_path(BOOK_ID)
    if not book_dir:
        print("Book not found")
        return
        
    epub_path = EpubManager.find_epub_file(book_dir)
    print(f"Checking EPUB: {epub_path}")
    
    with zipfile.ZipFile(epub_path, 'r') as z:
        print("\n--- Files in ZIP ---")
        for name in z.namelist():
            if 'xhtml' in name or 'html' in name:
                print(name)

if __name__ == "__main__":
    list_epub_files()
