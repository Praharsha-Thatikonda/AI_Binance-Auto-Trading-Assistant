import sqlite3
import os

DB_FILE = "web3.db"

def check_tables():
    if not os.path.exists(DB_FILE):
        print("web3.db not found. It will be created by SQLAlchemy if not present, but let's check.")
        # SQLAlchemy creates it on first connect if using create_all, which is in database.py
        # But we need to make sure the app has run create_all.
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"Tables in web3.db: {tables}")
    
    conn.close()

if __name__ == "__main__":
    check_tables()
