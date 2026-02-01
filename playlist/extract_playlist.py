from ytmusicapi import YTMusic
from os import path
import json
import re
import random

# Configuration
PLAYLIST_ID = "PLXlz4-GmC7VsuHrQgBg40CHHqFftdVNqJ"

# Setup Authentication
base_dir = path.dirname(__file__)
cfg_path = path.join(base_dir, '..', 'setup', 'headers_auth.cfg')

def sanitize_filename(name):
    """Sanitize string to be safe for filenames."""
    # Remove invalid characters
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

try:
    yt = YTMusic(cfg_path)
    
    print(f"Fetching playlist: {PLAYLIST_ID}...")
    # Fetch playlist with all tracks (limit=None)
    playlist = yt.get_playlist(PLAYLIST_ID, limit=None)
    
    playlist_title = playlist.get('title', 'Unknown_Playlist')
    safe_title = sanitize_filename(playlist_title)
    output_file = f"playlist_{safe_title}.json"
    
    tracks = playlist.get('tracks', [])
    print(f"Found {len(tracks)} tracks in '{playlist_title}'.")
    
    # Process & Clean Data for Siroco
    siroco_tracks = []
    for track in tracks:
        # Extract artist names
        artists_list = track.get('artists', [])
        if artists_list is None: 
             artist_names = []
        else:
             artist_names = [a.get('name') for a in artists_list if isinstance(a, dict) and 'name' in a]

        # Safe extraction of album
        album_data = track.get('album')
        album_name = album_data.get('name') if isinstance(album_data, dict) else None

        # Mock/Enriched Data
        clean_track = {
            "videoId": track.get('videoId'),
            "title": track.get('title'),
            "artists": artist_names,
            "album": album_name,
            "duration": track.get('duration_seconds'),
            "playlist": playlist_title,
            "popularity": random.randint(0, 100), # Mock: 0-100
            "demographic": random.choice(['Family', 'Couple', 'Social']), # Mock
            "energy": random.randint(1, 10), # Mock: 1-10
            "tags": [], # Placeholder: ytmusicapi playlist tracks rarely have categories
            "analysis": {
                "bpm": None,
                "key": None,
                "energy": None,
                "danceability": None
            },
            "tags": [] 
        }
        siroco_tracks.append(clean_track)

    # Save Cleaned JSON
    output_file_clean = "siroco_playlist.json"
    output_path_clean = path.join(base_dir, output_file_clean)
    
    with open(output_path_clean, 'w', encoding='utf-8') as f:
        json.dump(siroco_tracks, f, indent=4, ensure_ascii=False)
    print(f"Saved cleaned data to: {output_file_clean}")
        
except Exception as e:
    print(f"Error: {e}")
