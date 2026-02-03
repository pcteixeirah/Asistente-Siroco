import json
import random
import os
import time
import re
import yt_dlp
from os import path

# Configurations
PLAYLIST_JSON = "siroco_playlist.json"
PLAYLIST_DIR = "playlist"
DOWNLOAD_DIR = "assets"
TARGET_SUCCESS = 5

def setup_environment():
    """Ensure ffmpeg is valid in PATH."""
    winget_path = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WinGet\Links')
    if os.path.exists(winget_path):
        os.environ["PATH"] += os.pathsep + winget_path

def sanitize_filename(name):
    """Remove filesystem-unsafe characters and replace spaces with underscores."""
    name = re.sub(r'[<>:"/\\|?*]', '', name).strip()
    return re.sub(r'\s+', '_', name)

def download_tracks():
    base_dir = path.dirname(__file__)
    json_path = path.join(base_dir, '..', PLAYLIST_DIR, PLAYLIST_JSON)
    samples_dir = path.join(base_dir, '..', DOWNLOAD_DIR)

    # Load Playlist
    if not path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        all_tracks = json.load(f)

    # Shuffle tracks to try in random order
    random.shuffle(all_tracks)
    
    print(f"Goal: Download {TARGET_SUCCESS} tracks to '{DOWNLOAD_DIR}/'...")

    # yt-dlp Options
    # We set outtmpl dynamically inside loop, so here we set valid base options
    ydl_opts_base = {
        'format': 'bestaudio/best',
        'paths': {'home': samples_dir},
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
        # Anti-Bot Measures
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'sleep_interval': 3, # Sleep between internal requests
        'max_sleep_interval': 8,
        'nocheckcertificate': True,
    }

    setup_environment()
    
    success_count = 0
    # Iterate through ALL tracks until we hit target
    for track in all_tracks:
        if success_count >= TARGET_SUCCESS:
            break
            
        video_id = track.get('videoId')
        title = track.get('title', 'Unknown')
        # Handle multiple artists (take first or join)
        artists = track.get('artists', [])
        artist_str = artists[0] if artists else "Unknown Artist"
        
        # Clean Filename: "Artist - Title.mp3"
        clean_name = sanitize_filename(f"{artist_str} - {title}")
        # Note: yt-dlp/ffmpeg adds extension automatically, outtmpl needs just base
        
        # Skip if file already exists manually (to save bandwidth and time)
        expected_file = path.join(samples_dir, f"{clean_name}.mp3")
        if path.exists(expected_file):
            print(f"[Skip] Already exists: {clean_name}.mp3")
            success_count += 1
            continue

        ydl_opts = ydl_opts_base.copy()
        ydl_opts['outtmpl'] = f"{clean_name}.%(ext)s"

        try:
            print(f"Attempting: {clean_name} ({video_id})...")
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Explicit wait before request
            time.sleep(random.uniform(5.0, 10.0))
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            print(f" -> Success!")
            success_count += 1
            
        except Exception as e:
            # Catch 403 or other errors
            print(f" -> Failed: {e} (Skipping to next track)")
            # Longer wait on failure
            time.sleep(random.uniform(10.0, 15.0))

    if success_count < TARGET_SUCCESS:
        print(f"Finished. Could only download {success_count} tracks (ran out of candidates).")
    else:
        print(f"Done! {TARGET_SUCCESS} tracks secured.")

if __name__ == "__main__":
    download_tracks()
