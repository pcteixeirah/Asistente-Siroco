from ytmusicapi import YTMusic
from os import path
import json
import re

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
    
    # Save to JSON
    output_path = path.join(base_dir, output_file)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(tracks, f, indent=4, ensure_ascii=False)
        
    print(f"Saved to: {output_file}")
        
except Exception as e:
    print(f"Error: {e}")
