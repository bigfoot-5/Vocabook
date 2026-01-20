import os
from ebooklib import epub
import ebooklib

class EpubManager:
    @staticmethod
    def find_epub_file(book_dir):
        for root, dirs, files in os.walk(book_dir):
            for file in files:
                if file.lower().endswith('.epub') and not file.lower().endswith('original_epub'):
                        return os.path.join(root, file)
        return None

    @staticmethod
    def read_book(path):
        try:
            return epub.read_epub(path)
        except Exception as e:
            print(f"Failed to read EPUB: {e}")
            return None
