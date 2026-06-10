import sys
import argparse
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ebooklib import epub
from bs4 import BeautifulSoup
from src.calibre_db import CalibreDB
from src.epub_utils import EpubManager

import warnings
warnings.filterwarnings("ignore")

def scan_tokens(library_path, book_id, start_spine=0, end_spine=float('inf')):
    db = CalibreDB(library_path)
    book_dir = db.get_book_path(book_id)
    if not book_dir:
        print("0")
        return

    epub_path = EpubManager.find_epub_file(book_dir)
    if not epub_path:
        print("0")
        return

    try:
        book = epub.read_epub(epub_path)
        total_tokens = 0
        
        
        current_index = 0
        
        for item_id, _ in book.spine:
            item = book.get_item_with_id(item_id)
            if not item: continue
            
            if current_index < start_spine:
                current_index += 1
                continue
            if current_index > end_spine:
                break
                
            content = item.get_content()
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text(separator=' ')
                tokens = len(text.split())
                total_tokens += tokens
                
            current_index += 1
            
        print(total_tokens)
        
    except Exception as e:
        print("0")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--book_id", type=str, required=True)
    parser.add_argument("--library_path", type=str, required=True)
    parser.add_argument("--start_spine", type=int, default=0)
    parser.add_argument("--end_spine", type=int, default=100000)
    args = parser.parse_args()
    
    scan_tokens(args.library_path, args.book_id, args.start_spine, args.end_spine)
