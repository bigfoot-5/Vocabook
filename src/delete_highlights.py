from calibre_db import CalibreDB

# Configuration
LIBRARY_PATH = '/Users/karthiktalluri/Calibre Library'
BOOK_ID = 22

def main():
    print(f"Connecting to DB at {LIBRARY_PATH}...")
    db = CalibreDB(LIBRARY_PATH)
    
    confirm = input(f"Are you sure you want to delete ALL highlights for Book ID {BOOK_ID}? (y/n): ")
    if confirm.lower() == 'y':
        db.delete_book_highlights(BOOK_ID)
    else:
        print("Cancelled.")

if __name__ == "__main__":
    main()
