import os
import shutil
from src.calibre_db import CalibreDB
from src.epub_utils import EpubManager
from ebooklib import epub

LIBRARY_PATH = '/Users/karthiktalluri/Calibre Library'
BOOK_ID = 21

def main():
    print("Testing Read -> Write cycle without modification...")
    db = CalibreDB(LIBRARY_PATH)
    book_dir = db.get_book_path(BOOK_ID)
    epub_path = EpubManager.find_epub_file(book_dir)
    pass 
    if not epub_path:
        print("EPUB not found.")
        return

    print(f"Reading {epub_path}")
    book = EpubManager.read_book(epub_path)
    
    output_path = "test_output.epub"
    print(f"Writing to {output_path}")
    
    try:
        epub.write_epub(output_path, book)
        print("Success!")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
