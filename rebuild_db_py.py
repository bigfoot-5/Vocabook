import sqlite3
import os

DUMP_FILE = 'dump.sql'
NEW_DB = 'metadata_py_rebuilt.db'

def rebuild():
    if os.path.exists(NEW_DB):
        os.remove(NEW_DB)
        
    print(f"Reading {DUMP_FILE}...")
    with open(DUMP_FILE, 'r', encoding='utf-8') as f:
        sql_script = f.read()
        
    print(f"Executing script on {NEW_DB}...")
    conn = sqlite3.connect(NEW_DB)
    try:
        conn.executescript(sql_script)
        conn.commit()
        print("Rebuild successful.")
    except Exception as e:
        print(f"Error rebuilding: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    rebuild()
