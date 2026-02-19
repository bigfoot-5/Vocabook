from src.epub_injector import EpubInjector
import os

def test_scan():
    print("Initializing Injector...")
    try:
        injector = EpubInjector('/Users/karthiktalluri/Calibre Library')
        print("Injector initialized.")
    except Exception as e:
        print(f"Failed to init injector: {e}")
        return

    book_id = 10
    print(f"Scanning Book {book_id}...")
    try:
        count = injector.scan_book_tokens(book_id)
        print(f"Token Count: {count}")
    except Exception as e:
        print(f"Scan failed: {e}")

if __name__ == "__main__":
    test_scan()
