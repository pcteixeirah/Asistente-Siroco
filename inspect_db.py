
import sqlite3
import os
from core.config import load_config

config = load_config()
db_path = config["paths"]["database"]

if not os.path.exists(db_path):
    print(f"Error: Database file not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get list of tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print(f"Database: {db_path}")
print("-" * 30)

for table_name in tables:
    table = table_name[0]
    print(f"\nTable: {table}")
    
    # Get columns
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    col_names = [col[1] for col in columns]
    print(f"Columns: {', '.join(col_names)}")
    
    # Get first 3 rows
    cursor.execute(f"SELECT * FROM {table} LIMIT 3")
    rows = cursor.fetchall()
    
    if rows:
        print("First 3 rows:")
        for row in rows:
            print(f"  {row}")
    else:
        print("  (Table is empty)")

conn.close()
