import sqlite3
import json
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class SirocoRegistry:
    def __init__(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._create_table()
        self._migrate()

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
                    energy_rms REAL,
                    danceability REAL,
                    valence REAL,
                    spotify_id TEXT,
                    duration REAL,
                    last_analyzed TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    file_path_metadata TEXT,
                    error_type TEXT,
                    retry_count INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def _migrate(self):
        """Add new columns to existing databases without losing data."""
        migrations = [
            ("error_type", "TEXT"),
            ("retry_count", "INTEGER DEFAULT 0"),
            ("danceability", "REAL"),
            ("valence", "REAL"),
            ("spotify_id", "TEXT"),
            ("match_score", "REAL"),
            ("genre", "TEXT"),
            ("mood", "TEXT"),
            ("demographic", "TEXT"),
            ("energy_level", "TEXT"),
            ("time_of_day", "TEXT"),
        ]
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(tracks)")
                existing_cols = {row[1] for row in cursor.fetchall()}

                for col_name, col_type in migrations:
                    if col_name not in existing_cols:
                        cursor.execute(f"ALTER TABLE tracks ADD COLUMN {col_name} {col_type}")
                        logger.info(f"Migrated: added column '{col_name}' to tracks table.")
                conn.commit()
        except Exception as e:
            logger.error(f"Migration error: {e}")

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

    def get_all_tracks(self):
        """
        Returns a list of all tracks as dictionaries.
        """
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tracks")
                rows = cursor.fetchall()
                result = []
                for row in rows:
                    data = dict(row)
                    # Parse JSON fields
                    for field in ['artist', 'tags', 'file_path_metadata']:
                        if data.get(field):
                            try:
                                data[field] = json.loads(data[field])
                            except:
                                pass
                    result.append(data)
                return result
        except Exception as e:
            logger.error(f"Error getting all tracks: {e}")
            return []

    def add_track_metadata(self, yt_id, title, artist_list, album, playlist, popularity=None, demographic=None, tags=None, genre=None):
        """
        Initial insert of metadata. Uses INSERT OR IGNORE to avoid wiping existing analysis.
        """
        try:
            artist_json = json.dumps(artist_list) if artist_list else "[]"
            tags_json = json.dumps(tags) if tags else "[]"
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # INSERT OR IGNORE preserves existing analysis data (BPM, Key, etc.)
                cursor.execute("""
                    INSERT OR IGNORE INTO tracks (
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

    def update_analysis(self, yt_id, bpm, key, energy=None, duration=None, danceability=None, valence=None, spotify_id=None, match_score=None):
        """
        Update with analysis results. Status -> success. Resets error fields.
        Accepts partial data (some fields may be None depending on source).
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE tracks 
                    SET bpm = ?, key = ?, energy_rms = ?, duration = ?, 
                        danceability = ?, valence = ?, spotify_id = ?,
                        match_score = ?,
                        status = 'success', last_analyzed = ?,
                        error_type = NULL, retry_count = 0
                    WHERE yt_id = ?
                """, (bpm, key, energy, duration, danceability, valence, spotify_id, match_score, datetime.now(), yt_id))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating analysis for {yt_id}: {e}")
            return False

    def mark_failed(self, yt_id, error_type="unknown"):
        """
        Mark track as failed with error classification.
        Increments retry_count for tracking purposes.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE tracks 
                    SET status = 'failed', last_analyzed = ?, 
                        error_type = ?, retry_count = COALESCE(retry_count, 0) + 1
                    WHERE yt_id = ?
                """, (datetime.now(), error_type, yt_id))
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

    def update_tags(self, yt_id, genre, mood, demographic, energy_level, time_of_day):
        """
        Update semantic tags for a track. Values are JSON-serialized lists.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE tracks 
                    SET genre = ?, mood = ?, demographic = ?, 
                        energy_level = ?, time_of_day = ?
                    WHERE yt_id = ?
                """, (
                    json.dumps(genre) if isinstance(genre, list) else genre,
                    json.dumps(mood) if isinstance(mood, list) else mood,
                    json.dumps(demographic) if isinstance(demographic, list) else demographic,
                    energy_level,
                    json.dumps(time_of_day) if isinstance(time_of_day, list) else time_of_day,
                    yt_id
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating tags for {yt_id}: {e}")
            return False

    def get_tracks_for_tagging(self):
        """
        Returns tracks with status='success' that haven't been tagged yet.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT yt_id, title, artist, bpm, key, danceability
                    FROM tracks 
                    WHERE status = 'success' AND (genre IS NULL OR genre = '')
                """)
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    artist_str = ""
                    try:
                        arts = json.loads(row[2]) if row[2] else []
                        if arts and isinstance(arts[0], dict):
                            artist_str = arts[0].get('name', '')
                        elif arts:
                            artist_str = str(arts[0])
                    except (json.JSONDecodeError, IndexError):
                        artist_str = str(row[2] or "")
                    
                    results.append({
                        "yt_id": row[0],
                        "title": row[1],
                        "artist": artist_str,
                        "bpm": row[3],
                        "key": row[4],
                        "danceability": row[5],
                    })
                return results
        except Exception as e:
            logger.error(f"Error getting tracks for tagging: {e}")
            return []
