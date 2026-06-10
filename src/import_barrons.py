import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Vocabulary
import os

CSV_PATH = 'Barrons333_words.csv'
DB_PATH = 'sqlite:///vocabook.db'

def import_barrons_words():
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found in the current directory.")
        return

    print(f"Reading {CSV_PATH}...")
    try:

        df = pd.read_csv(CSV_PATH)
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        return


    required_cols = ['word', 'definition']
    if not all(col in df.columns for col in required_cols):
        print(f"CSV missing required columns. Found: {df.columns}")
        return

    print(f"Connecting to database {DB_PATH}...")
    engine = create_engine(DB_PATH, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    count = 0
    skipped = 0
    

    for index, row in df.iterrows():
        word_str = str(row['word']).strip()
        def_str = str(row['definition']).strip()
        

        if not word_str or word_str.lower() == 'nan':
            continue


        existing = session.query(Vocabulary).filter_by(word=word_str).first()
        if existing:
            skipped += 1
            continue


        new_word = Vocabulary(
            word=word_str,
            definition=def_str
        )
        session.add(new_word)
        count += 1


    session.commit()
    session.close()
    
    print(f"Import complete. Added {count} new words. Skipped {skipped} duplicates.")

if __name__ == "__main__":
    import_barrons_words()
