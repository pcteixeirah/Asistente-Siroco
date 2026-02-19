
from ytmusicapi import YTMusic
from os import path
import json
import re
import random
import logging
import os

logger = logging.getLogger(__name__)

class PlaylistScanner:
    def __init__(self, playlist_id="PLXlz4-GmC7VsuHrQgBg40CHHqFftdVNqJ"):
        self.playlist_id = playlist_id
        self.base_dir = path.dirname(__file__)
        self.root_dir = path.join(self.base_dir, '..')
        self.auth_path = path.join(self.root_dir, 'setup', 'headers_auth.cfg')
        
        # Initialize YTMusic
        if path.exists(self.auth_path):
            self.yt = YTMusic(self.auth_path)
            logger.info("Authenticated YTMusic user.")
        else:
            self.yt = YTMusic()
            logger.warning("Using unauthenticated YTMusic.")

    def _sanitize_filename(self, name):
        """Sanitize string to be safe for filenames."""
        return re.sub(r'[<>:"/\\|?*]', '', name).strip()

    def sync_playlist(self, db):
        """
        Fetches live playlist and syncs metadata to the database.
        Returns the list of tracks from the DB.
        """
        try:
            logger.info(f"Fetching playlist: {self.playlist_id}...")
            # Fetch playlist with all tracks
            playlist_data = self.yt.get_playlist(self.playlist_id, limit=None)
            tracks = playlist_data.get('tracks', [])
            playlist_title = playlist_data.get('title', 'Unknown_Playlist')
            
            logger.info(f"Found {len(tracks)} tracks in '{playlist_title}'.")
            
            processed_count = 0
            
            for track in tracks:
                video_id = track.get('videoId')
                if not video_id:
                    continue
                    
                # Extract basic info
                title = track.get('title')
                
                # Extract artists
                artists_list = track.get('artists', [])
                artist_names = [a.get('name') for a in artists_list if isinstance(a, dict) and 'name' in a] if artists_list else []
                
                album_data = track.get('album')
                album_name = album_data.get('name') if isinstance(album_data, dict) else None
                
                # Add to DB (non-destructive insert)
                success = db.add_track_metadata(
                    yt_id=video_id,
                    title=title,
                    artist_list=artist_names,
                    album=album_name,
                    playlist=playlist_title
                )
                if success:
                    processed_count += 1

            logger.info(f"Synced {processed_count} tracks to DB.")
            
            # Return fresh list from DB source of truth
            return db.get_all_tracks()

        except Exception as e:
            logger.error(f"Error syncing playlist: {e}")
            return []
