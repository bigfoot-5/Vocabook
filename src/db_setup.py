import sqlite3
import os

# Use absolute path or relative to execution? User uses relative 'vocabook.db' usually.
# Assuming run from project root.
DB_PATH = 'vocabook.db'

def setup_database():
    print(f"Connecting to database at {os.path.abspath(DB_PATH)}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Schema definitions
    # Added IF NOT EXISTS to prevent errors if running multiple times
    schemas = [
        """
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            definition TEXT,
            
            -- FSRS State Columns (Required for the algorithm)
            due TIMESTAMP,          -- When the card needs to be shown next (UTC)
            stability REAL,         -- Memory stability (S)
            difficulty REAL,        -- Difficulty (D)
            elapsed_days INTEGER,   -- Days since the last review
            scheduled_days INTEGER, -- The interval that was scheduled last time
            reps INTEGER,           -- Total review count
            lapses INTEGER,         -- How many times you forgot it
            state INTEGER,          -- 0:New, 1:Learning, 2:Review, 3:Relearning
            last_review TIMESTAMP   -- When you last saw this card
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS review_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id INTEGER,
            rating INTEGER,         -- 1:Again, 2:Hard, 3:Good, 4:Easy
            scheduled_days INTEGER, -- What the interval WAS scheduled for
            elapsed_days INTEGER,   -- How long you ACTUALLY waited
            review_date TIMESTAMP,  -- When this specific review happened
            state INTEGER,          -- State of the card BEFORE this review
            FOREIGN KEY(word_id) REFERENCES words(id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS fsrs_parameters (
            id INTEGER PRIMARY KEY,
            weights TEXT,           -- JSON string of the 17 weights
            request_retention REAL  -- e.g., 0.9 (90% retention target)
        );
        """
    ]

    for schema in schemas:
        try:
            cursor.execute(schema)
            # Extract table name for logging
            table_name_start = schema.find("TABLE IF NOT EXISTS") + len("TABLE IF NOT EXISTS")
            table_name_end = schema.find("(", table_name_start)
            table_name = schema[table_name_start:table_name_end].strip()
            print(f"Ensured table '{table_name}' exists.")
        except Exception as e:
            print(f"Error executing schema for table: {e}")

    conn.commit()
    conn.close()
    print("Database setup complete.")

if __name__ == "__main__":
    setup_database()
