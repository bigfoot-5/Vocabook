import pandas as pd
import sqlite3
import os

CSV_PATH = 'GRE Master Wordlist 5349.csv'
DB_PATH = 'vocabook.db'

def import_gre_words():
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found.")
        return

    print(f"Reading {CSV_PATH}...")
    # Read CSV, handle potential encoding or quoting issues if needed
    try:
        df = pd.read_csv(CSV_PATH)
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        return

    # Check columns
    required_cols = ['Word', 'Synonym']
    if not all(col in df.columns for col in required_cols):
        print(f"CSV missing required columns. Found: {df.columns}")
        return

    print(f"Connecting to database {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    count = 0
    skipped_bad_rows = 0
    
    for index, row in df.iterrows():
        word = str(row['Word']).strip()
        definition = str(row['Synonym']).strip()
        
        # Heuristic 1: Fix "abolish cancel..." where synonym is nan
        if (definition.lower() == 'nan' or not definition) and ' ' in word:
            # Assume incorrectly parsed. Split at first space.
            parts = word.split(' ', 1)
            word = parts[0]
            definition = parts[1]
            
        # Heuristic 2: Clean word (remove parens if they are just variants? No, keep logic simple first)
        # Actually, let's keep variants in DB, but handle them in highlighter?
        # Or store cleaned word?
        
        if not word or word.lower() == 'nan':
            continue

        # Check if word exists
        cursor.execute("SELECT id FROM words WHERE word = ?", (word,))
        if cursor.fetchone():
            continue

        cursor.execute("""
            INSERT INTO words (
                word, definition, 
                state, reps, lapses, elapsed_days, scheduled_days
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (word, definition, 0, 0, 0, 0, 0))
        count += 1
        
        if count % 500 == 0:
            print(f"Processed {count} words...")

    conn.commit()
    conn.close()
    print(f"Import complete. Added {count} new words.")

if __name__ == "__main__":
    import_gre_words()
