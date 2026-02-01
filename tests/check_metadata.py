from ytmusicapi import YTMusic
import yt_dlp
import json

# Setup
yt = YTMusic('setup/headers_auth.cfg')
VIDEO_ID = "7gPOfcUbTFc" # Soy Colombiano from AZC

print("--- YTMusic.get_song ---")
try:
    song_details = yt.get_song(VIDEO_ID)
    # views usually in videoDetails -> viewCount
    print(json.dumps(song_details, indent=2))
except Exception as e:
    print(e)

print("\n--- yt-dlp dump-json ---")
try:
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={VIDEO_ID}", download=False)
        # Check for view_count, tags, categories
        print("Views:", info.get('view_count'))
        print("Tags:", info.get('tags'))
        print("Categories:", info.get('categories'))
        print("Like Count:", info.get('like_count'))
except Exception as e:
    print(e)
