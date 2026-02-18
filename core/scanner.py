
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
        self.playlist_json_path = path.join(self.root_dir, 'playlist', 'siroco_playlist.json')
        
        # Ensure playlist directory exists
        os.makedirs(path.dirname(self.playlist_json_path), exist_ok=True)
        
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

    def sync_playlist(self):
        """
        Fetches live playlist, merges with local JSON, saves back to JSON.
        Returns the list of tracks.
        """
        try:
            logger.info(f"Fetching playlist: {self.playlist_id}...")
            # Fetch playlist with all tracks
            playlist_data = self.yt.get_playlist(self.playlist_id, limit=None)
            tracks = playlist_data.get('tracks', [])
            playlist_title = playlist_data.get('title', 'Unknown_Playlist')
            
            logger.info(f"Found {len(tracks)} tracks in '{playlist_title}'.")
            
            # Load existing JSON for merging
            existing_tracks = {}
            if path.exists(self.playlist_json_path):
                try:
                    with open(self.playlist_json_path, 'r', encoding='utf-8') as f:
                        old_data = json.load(f)
                        for t in old_data:
                            existing_tracks[t['videoId']] = t
                except Exception as e:
                    logger.warning(f"Could not load existing playlist JSON: {e}")

            siroco_tracks = []
            
            for track in tracks:
                video_id = track.get('videoId')
                if not video_id:
                    continue
                    
                # If track exists locally, preserve its rich metadata
                if video_id in existing_tracks:
                    # Update basic metadata just in case (title changes?)
                    # For now, let's trust the API for title/artist/duration
                    existing = existing_tracks[video_id]
                    
                    # Update basic info from live API
                    existing['title'] = track.get('title')
                    existing['duration'] = track.get('duration_seconds')
                    
                    # Extract artists
                    artists_list = track.get('artists', [])
                    artist_names = [a.get('name') for a in artists_list if isinstance(a, dict) and 'name' in a] if artists_list else []
                    existing['artists'] = artist_names
                    
                    album_data = track.get('album')
                    existing['album'] = album_data.get('name') if isinstance(album_data, dict) else None

                    # Set playlist name (if changed)
                    existing['playlist'] = playlist_title
                    
                    siroco_tracks.append(existing)
                else:
                    # New Track -> Initialize with Defaults
                    artists_list = track.get('artists', [])
                    artist_names = [a.get('name') for a in artists_list if isinstance(a, dict) and 'name' in a] if artists_list else []
                    
                    album_data = track.get('album')
                    album_name = album_data.get('name') if isinstance(album_data, dict) else None
                    
                    clean_track = {
                        "videoId": video_id,
                        "title": track.get('title'),
                        "artists": artist_names,
                        "album": album_name,
                        "duration": track.get('duration_seconds'),
                        "playlist": playlist_title,
                        # Default / To be analyzed
                        "popularity": None, 
                        "demographic": None,
                        "energy": None,
                        "tags": [],
                        "analysis": {
                            "bpm": None,
                            "key": None,
                            "energy": None,
                            "danceability": None
                        }
                    }
                    siroco_tracks.append(clean_track)

            # Save Processed JSON
            with open(self.playlist_json_path, 'w', encoding='utf-8') as f:
                json.dump(siroco_tracks, f, indent=4, ensure_ascii=False)
            
            logger.info(f"Synced {len(siroco_tracks)} tracks to {self.playlist_json_path}")
            return siroco_tracks

        except Exception as e:
            logger.error(f"Error syncing playlist: {e}")
            return []

    def get_tracks(self):
        """Loads tracks from the local JSON file."""
        if path.exists(self.playlist_json_path):
            with open(self.playlist_json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
