import sqlite3
import os
import pandas as pd

db_path = os.path.join("data", "siroco_registry.db")
# I recall the backup name from previous turn
backup_table = "tracks_backup_20260219_022453"

try:
    conn = sqlite3.connect(db_path)
    
    print(f"--- COMPARISON: {backup_table} vs 'tracks' (New Run) ---")
    
    # 1. Count Statuses in New Run
    print("\n[New Run Stats]")
    df_new = pd.read_sql_query("SELECT status, error_type, count(*) as count FROM tracks GROUP BY status, error_type", conn)
    print(df_new)
    
    # 2. Compare with Backup
    print(f"\n[Backup Stats] ({backup_table})")
    df_backup = pd.read_sql_query(f"SELECT status, error_type, count(*) as count FROM {backup_table} GROUP BY status, error_type", conn)
    print(df_backup)
    
    # 3. Check consistency
    cursor = conn.cursor()
    cursor.execute(f"SELECT count(*) FROM {backup_table}")
    cnt_backup = cursor.fetchone()[0]
    cursor.execute("SELECT count(*) FROM tracks")
    cnt_new = cursor.fetchone()[0]
    
    print(f"\nTotal Tracks: Backup={cnt_backup}, New={cnt_new}")
    
    # 4. Analyze Errors specifically
    print("\n[Failure Analysis]")
    df_errors = pd.read_sql_query("SELECT error_type, count(*) as count FROM tracks WHERE status='failed' GROUP BY error_type", conn)
    print(df_errors)

    conn.close()

except Exception as e:
    print(f"Error: {e}")
