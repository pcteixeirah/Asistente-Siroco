import os
import sys
import time
import random
import logging
import argparse
from core.database import SirocoRegistry
from core.downloader import LowFiDownloader
from core.analyzer import AudioAnalyzer
from core.scanner import PlaylistScanner

# Setup Logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/process.log", encoding='utf-8', mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Constants
PLAYLIST_ID_DEFAULT = "PLXlz4-GmC7VsuHrQgBg40CHHqFftdVNqJ"

def main():
    parser = argparse.ArgumentParser(description="Siroco Musical Analysis Proxy")
    parser.add_argument("--playlist", type=str, default=PLAYLIST_ID_DEFAULT, help="YouTube Playlist ID")
    args = parser.parse_args()

    logger.info(f"Starting Proxy Workflow for Playlist ID: {args.playlist}")

    # Initialize Modules
    try:
        db = SirocoRegistry()
        downloader = LowFiDownloader()
        analyzer = AudioAnalyzer()
        scanner = PlaylistScanner(playlist_id=args.playlist)
    except Exception as e:
        logger.critical(f"Failed to initialize modules: {e}")
        return

    # 1. Sync Playlist (Source of Truth)
    logger.info("Step 1: Syncing Playlist (Live -> Local JSON)...")
    tracks = scanner.sync_playlist()
    
    if not tracks:
        logger.error("No tracks found or sync failed. Exiting.")
        return

    logger.info(f"Sync complete. Local JSON contains {len(tracks)} tracks.")

    # 2. Process Tracks
    logger.info("Step 2: Processing Tracks (Download -> Analyze -> Store)...")
    BATCH_SIZE = 5
    processed_count = 0

    for i, track in enumerate(tracks):
        yt_id = track.get('videoId')
        title = track.get('title')
        artists = track.get('artists', [])
        album = track.get('album')
        playlist_name = track.get('playlist')
        
        # Extended Metadata
        popularity = track.get('popularity')
        demographic = track.get('demographic')
        tags = track.get('tags', [])

        if not yt_id:
            continue

        # Check Registry
        cached_data = db.check_registry(yt_id)
        if cached_data:
             if cached_data['status'] == 'success':
                 logger.info(f"[{i+1}/{len(tracks)}] Skipping '{title}' (Already analyzed). BPM: {cached_data['bpm']}")
                 continue
             elif cached_data['status'] == 'failed':
                 logger.info(f"[{i+1}/{len(tracks)}] Re-trying failed track: '{title}'")
        
        logger.info(f"[{i+1}/{len(tracks)}] Processing: {title}...")

        # Update Metadata in DB (even if we fail analysis later, we want metadata stored)
        db.add_track_metadata(
            yt_id, title, artists, album, playlist_name, 
            popularity, demographic, tags
        )

        # Download & Analyze
        try:
            # Download
            logger.info("  -> Downloading...")
            audio_path = downloader.download_audio(yt_id)
            
            # Analyze
            logger.info("  -> Analyzing...")
            algo_res = analyzer.analyze_track(audio_path) # Returns dict of features
            
            # Update DB with Analysis
            db.update_analysis(
                yt_id, 
                algo_res['bpm'], 
                algo_res['key'], 
                algo_res['energy_rms'], 
                algo_res['duration']
            )
            logger.info(f"  -> Success! BPM: {algo_res['bpm']}, Key: {algo_res['key']}")
            processed_count += 1

        except Exception as e:
            logger.error(f"  -> Failed: {e}")
            db.mark_failed(yt_id)
        
        # Batch Delay to avoid rate limiting
        if processed_count > 0 and processed_count % BATCH_SIZE == 0:
             wait_time = random.randint(2, 5)
             logger.info(f"Batch limit reached. Sleeping {wait_time}s...")
             time.sleep(wait_time)

if __name__ == "__main__":
    main()
