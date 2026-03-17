"""
SIROCO Playlist Generator

Queries the enriched SQLite database (with LLM tags) to generate
time-of-day specific YouTube Music playlists.
"""

import logging
from core.database import SirocoRegistry
from ytmusicapi import YTMusic

logger = logging.getLogger(__name__)

class PlaylistGenerator:
    def __init__(self, db_path: str, auth_cfg: str, schedule_config: dict):
        self.db = SirocoRegistry(db_path=db_path)
        self.schedule_config = schedule_config
        
        try:
            # ytmusicapi client using user's authentication
            self.yt = YTMusic(auth_cfg)
            logger.info("YTMusic authenticated successfully.")
        except Exception as e:
            logger.error(f"Failed to authenticate YTMusic. Run auth_ytmusic.py first. Error: {e}")
            self.yt = None

    def generate_for_timeslot(self, timeslot: str) -> list:
        """
        Query DB for tracks matching the timeslot.
        Returns a list of dicts with track info and yt_id.
        """
        if timeslot not in self.schedule_config:
            logger.error(f"Unknown timeslot: {timeslot}")
            return []

        # Get the target duration from config (default 120 mins)
        target_mins = self.schedule_config.get("target_duration_minutes", 120)
        # Assume average track length is 3.5 minutes
        track_limit = int(target_mins / 3.5)

        logger.info(f"Generating '{timeslot}' playlist (Target: {target_mins}m, ~{track_limit} tracks)")

        query = '''
            SELECT title, artist, yt_id, energy_level, mood
            FROM tracks 
            WHERE status = 'success'
              AND time_of_day LIKE ?
              AND yt_id IS NOT NULL
            ORDER BY RANDOM()
            LIMIT ?
        '''
        
        # time_of_day is stored as a JSON array string: '["morning", "afternoon"]'
        # We use a simple LIKE match.
        search_pattern = f'%"{timeslot}"%'
        
        try:
            with self.db._get_connection() as conn:
                conn.row_factory = __import__('sqlite3').Row
                cursor = conn.cursor()
                cursor.execute(query, (search_pattern, track_limit))
                results = cursor.fetchall()
                
            tracks = [dict(r) for r in results]
            logger.info(f"Found {len(tracks)} tracks for timeslot '{timeslot}'")
            return tracks
        except Exception as e:
            logger.error(f"Database query failed for timeslot {timeslot}: {e}")
            return []

    def publish_to_ytmusic(self, playlist_name: str, tracks: list, description: str = "") -> str:
        """
        Creates a new YT Music playlist.
        """
        if not self.yt:
            logger.error("Cannot publish: YTMusic not authenticated.")
            return None

        yt_ids = [t["yt_id"] for t in tracks if t.get("yt_id")]
        
        if not yt_ids:
            logger.warning(f"No valid YouTube IDs to publish for '{playlist_name}'")
            return None

        try:
            # Create a brand new playlist
            logger.info(f"Publishing playlist '{playlist_name}' to YT Music with {len(yt_ids)} tracks...")
            playlist_id = self.yt.create_playlist(
                title=playlist_name,
                description=description,
                privacy_status="PRIVATE",  # Make them private by default
                video_ids=yt_ids
            )
            
            # The API sometimes returns a dict or directly the ID string depending on the version
            if isinstance(playlist_id, dict):
                 pid = playlist_id.get('playlistId', str(playlist_id))
            else:
                 pid = playlist_id
                 
            logger.info(f"✅ Playlist created successfully! ID: {pid}")
            return pid
            
        except Exception as e:
            logger.error(f"Failed to create playlist '{playlist_name}': {e}")
            return None
