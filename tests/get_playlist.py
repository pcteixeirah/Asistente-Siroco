from ytmusicapi import YTMusic
from os import path
import random
import pprint

# 1. Setup Authentication
# Construct path relative to this script to locate headers_auth.cfg in setup/
base_dir = path.dirname(__file__)
cfg_path = path.join(base_dir, '..', 'setup', 'headers_auth.cfg')

try:
    yt = YTMusic(cfg_path)
    print("YTMusic initialized successfully.\n")
    
    # 2. Get Playlist Details
    # Playlist: Salsa de verdad
    playlist_id = "PLuaL8D_ptxG4k_Rl_bQIvsSkrnu_mnbD5"
    
    print(f"Fetching playlist: {playlist_id}...")
    playlist = yt.get_playlist(playlist_id)
    
    print(f"Playlist Name: {playlist.get('title', 'Unknown')}")
    print(f"Total Tracks: {playlist.get('trackCount', 0)}\n")
    
    # 3. Extract Tracks
    tracks = playlist.get('tracks', [])
    
    if not tracks:
        print("No tracks found in this playlist.")
    else:
        # 4. Select 10 Random Tracks
        # If fewer than 10, take all of them
        num_to_pick = min(10, len(tracks))
        selected_tracks = random.sample(tracks, num_to_pick)
        
        print(f"--- Selected {num_to_pick} Random Tracks ---")
        for i, track in enumerate(selected_tracks, 1):
            title = track.get('title', 'Unknown')
            # Artists is a list of dicts: [{'name': 'Artist', 'id': '...'}, ...]
            artists_list = track.get('artists', [])
            artists_str = ", ".join([a.get('name', 'Unknown') for a in artists_list])
            video_id = track.get('videoId', 'Unknown')
            
            print(f"{i}. Title: {title}")
            print(f"   Artists: {artists_str}")
            print(f"   Video ID: {video_id}")
            # Ensure we print the keys requested: playlistId (context), title, artists
            print(f"   Playlist ID: {playlist_id}") 
            print("-" * 30)

except Exception as e:
    print(f"An error occurred: {e}")
