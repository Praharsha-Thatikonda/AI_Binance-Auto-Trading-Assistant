import sqlite3
import os

DB_FILE = "wallet.db"

def check_and_fix_tables():
    if not os.path.exists(DB_FILE):
        print("wallet.db not found.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        # Check for web3_balances
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='web3_balances'")
        if not cursor.fetchone():
            print("Creating web3_balances table...")
            cursor.execute('''
                CREATE TABLE web3_balances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    currency VARCHAR,
                    amount FLOAT,
                    updated_at VARCHAR
                )
            ''')
            cursor.execute("CREATE INDEX ix_web3_balances_user_id ON web3_balances (user_id)")
            cursor.execute("CREATE INDEX ix_web3_balances_currency ON web3_balances (currency)")
            cursor.execute("CREATE INDEX ix_web3_balances_id ON web3_balances (id)")
            
        print("Database check complete.")
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_and_fix_tables()
