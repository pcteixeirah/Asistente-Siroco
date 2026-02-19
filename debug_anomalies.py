import sqlite3
import os

db_path = os.path.join(os.getcwd(), 'data', 'siroco_registry.db')
print(f"Checking DB at: {db_path}")
try:
    if not os.path.exists(db_path):
        print("DB FILE NOT FOUND!")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n--- SUMMARY STATS ---")
    cursor.execute("SELECT status, error_type, count(*) FROM tracks GROUP BY status, error_type")
    for r in cursor.fetchall(): print(r)

    print("\n--- RETRY COUNTS ---")
    cursor.execute("SELECT retry_count, count(*) FROM tracks GROUP BY retry_count")
    for r in cursor.fetchall(): print(r)

    print("\n--- RECENTLY UPDATED (Last 5) ---")
    cursor.execute("SELECT yt_id, status, last_analyzed FROM tracks ORDER BY last_analyzed DESC LIMIT 5")
    for r in cursor.fetchall(): print(r)
    
    conn.close()
except Exception as e: print(e)
