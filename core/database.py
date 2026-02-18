import sqlite3
import json
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class SirocoRegistry:
    def __init__(self, db_path="data/siroco_registry.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._create_table()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _create_table(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tracks (
                    yt_id TEXT PRIMARY KEY,
                    title TEXT,
                    artist TEXT,
                    album TEXT,
                    playlist TEXT,
                    genre TEXT,
                    popularity INTEGER,
                    demographic TEXT,
                    tags TEXT,
                    bpm INTEGER,
                    key TEXT,
                    energy_rms INTEGER,
                    duration REAL,
                    last_analyzed TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    file_path_metadata TEXT
                )
            """)
            conn.commit()

    def check_registry(self, yt_id):
        """
        Check if track exists and is valid.
        Returns dict with track data if exists, False otherwise.
        """
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tracks WHERE yt_id = ?", (yt_id,))
                row = cursor.fetchone()
                
                if row:
                    data = dict(row)
                   
                    if data['status'] == 'failed':
                        return False 
                        
                    # Parse JSON fields
                    for field in ['artist', 'tags', 'file_path_metadata']:
                        if data.get(field):
                            try:
                                data[field] = json.loads(data[field])
                            except:
                                pass
                            
                    return data
                return False
        except Exception as e:
            logger.error(f"Error checking registry for {yt_id}: {e}")
            return False

    def add_track_metadata(self, yt_id, title, artist_list, album, playlist, popularity=None, demographic=None, tags=None, genre=None):
        """
        Initial insert of metadata. Status -> pending.
        """
        try:
            artist_json = json.dumps(artist_list) if artist_list else "[]"
            tags_json = json.dumps(tags) if tags else "[]"
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Use INSERT OR REPLACE to update metadata if it changes in JSON
                cursor.execute("""
                    INSERT OR REPLACE INTO tracks (
                        yt_id, title, artist, album, playlist, genre, 
                        popularity, demographic, tags, 
                        status, last_analyzed
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """, (yt_id, title, artist_json, album, playlist, genre, 
                      popularity, demographic, tags_json, datetime.now()))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding track metadata {yt_id}: {e}")
            return False

    def update_analysis(self, yt_id, bpm, key, energy, duration):
        """
        Update with analysis results. Status -> success.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE tracks 
                    SET bpm = ?, key = ?, energy_rms = ?, duration = ?, status = 'success', last_analyzed = ?
                    WHERE yt_id = ?
                """, (bpm, key, energy, duration, datetime.now(), yt_id))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating analysis for {yt_id}: {e}")
            return False

    def mark_failed(self, yt_id):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE tracks SET status = 'failed', last_analyzed = ? WHERE yt_id = ?", 
                               (datetime.now(), yt_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Error marking failure for {yt_id}: {e}")

    def update_file_metadata(self, yt_id, file_metadata):
        try:
             metadata_json = json.dumps(file_metadata)
             with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE tracks SET file_path_metadata = ? WHERE yt_id = ?", 
                               (metadata_json, yt_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Error updating file metadata for {yt_id}: {e}")
