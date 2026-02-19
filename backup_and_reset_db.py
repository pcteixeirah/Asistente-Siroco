import sqlite3
import os
from datetime import datetime

db_path = os.path.join("data", "siroco_registry.db")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_table = f"tracks_backup_{timestamp}"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get current count
    cursor.execute("SELECT Count(*) FROM tracks")
    initial_count = cursor.fetchone()[0]
    print(f"Current tracks count: {initial_count}")
    
    # Create Backup
    print(f"Creating backup table: {backup_table}")
    cursor.execute(f"CREATE TABLE {backup_table} AS SELECT * FROM tracks")
    
    # Verify Backup
    cursor.execute(f"SELECT Count(*) FROM {backup_table}")
    backup_count = cursor.fetchone()[0]
    print(f"Backup tracks count: {backup_count}")
    
    if initial_count == backup_count:
        # Clear Data
        print("Clearing 'tracks' table...")
        cursor.execute("DELETE FROM tracks")
        conn.commit()
        
        # Verify Empty
        cursor.execute("SELECT Count(*) FROM tracks")
        final_count = cursor.fetchone()[0]
        print(f"Final 'tracks' count: {final_count}")
        print("Database reset successful.")
    else:
        print("ERROR: Backup count does not match! Aborting clear.")
        
    conn.close()

except Exception as e:
    print(f"Error: {e}")
