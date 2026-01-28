import json
import random
import os
import yt_dlp
from os import path

# Configurations
PLAYLIST_JSON = "siroco_playlist.json"
DOWNLOAD_DIR = "samples"
SAMPLE_SIZE = 5

def setup_environment():
    """Ensure ffmpeg is valid in PATH."""
    # Common location for Winget installs usually not picked up immediately
    winget_path = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WinGet\Links')
    if os.path.exists(winget_path):
        os.environ["PATH"] += os.pathsep + winget_path
        print(f"Temporarily added to PATH: {winget_path}")

def download_tracks():
    base_dir = path.dirname(__file__)
    json_path = path.join(base_dir, PLAYLIST_JSON)
    samples_dir = path.join(base_dir, '..', DOWNLOAD_DIR)

    # Load Playlist
    if not path.exists(json_path):
        print(f"Error: {json_path} not found. Run extract_playlist.py first.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        tracks = json.load(f)

    # Filter tracks that haven't been downloaded yet
    available_tracks = [t for t in tracks if not t.get('filepath')]
    
    if not available_tracks:
        print("All tracks already downloaded (or filepath set).")
        return

    # Select Random Samples
    upper_limit = min(len(available_tracks), SAMPLE_SIZE)
    selection = random.sample(available_tracks, upper_limit)
    
    print(f"Selected {upper_limit} random tracks to download...")

    # yt-dlp Options
    ydl_opts = {
        'format': 'bestaudio/best',
        'paths': {'home': samples_dir},
        'outtmpl': '%(title)s [%(id)s].%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
        # 'ffmpeg_location': '...' # Optional if PATH fails
    }

    # Setup environment for ffmpeg
    setup_environment()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for track in selection:
            video_id = track.get('videoId')
            try:
                print(f"Downloading: {track.get('title')} ({video_id})...")
                url = f"https://www.youtube.com/watch?v={video_id}"
                
                # Download
                info = ydl.extract_info(url, download=True)
                
                # Get filename
                # yt-dlp processed filename can be tricky to predict perfectly without 'prepare_filename'
                # But since we use a fixed template, we can construct it or read from info
                filename = ydl.prepare_filename(info)
                # Post-processing changes extension to mp3
                final_filename = path.splitext(path.basename(filename))[0] + ".mp3"
                
                # Update Track Object
                # path.abspath would be better, but relative to project root is good for portability
                # We'll store: samples/filename.mp3
                relative_path = path.join(DOWNLOAD_DIR, final_filename).replace('\\', '/')
                track['filepath'] = relative_path
                print(f" -> Success: {relative_path}")
                
            except Exception as e:
                print(f" -> Failed: {e}")

    # Save Updated JSON
    print("Updating playlist JSON...")
    # We need to update the ORIGINAL list 'tracks' with the modifications made to objects in 'selection'
    # Since 'selection' contains references to objects in 'tracks', modifying 'track' inside the loop 
    # should update the main list directly.
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(tracks, f, indent=4, ensure_ascii=False)
    print("Done.")

if __name__ == "__main__":
    download_tracks()
