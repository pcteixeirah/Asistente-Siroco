import os
import sys
import time
import random
import logging
import argparse
from core.config import load_config
from core.errors import classify_error
from core.database import SirocoRegistry
from core.analyzer import AudioAnalyzer
from core.scanner import PlaylistScanner

# Circuit breaker: abort if this many consecutive tracks fail with the same error
CIRCUIT_BREAKER_THRESHOLD = 20

def main():
    # Load centralized config
    config = load_config()

    # Setup Logging
    log_dir = os.path.dirname(config["paths"]["log_file"])
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config["paths"]["log_file"], encoding='utf-8', mode='w'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Siroco Musical Analysis Workflow (Spotify API)")
    parser.add_argument(
        "--playlist", type=str,
        default=config["playlist"]["default_id"],
        help="YouTube Playlist ID"
    )
    args = parser.parse_args()

    logger.info(f"Starting Workflow for Playlist ID: {args.playlist}")

    # Initialize Modules
    try:
        db = SirocoRegistry(db_path=config["paths"]["database"])
        analyzer = AudioAnalyzer(config=config.get("spotify", {}))
        scanner = PlaylistScanner(
            playlist_id=args.playlist,
            auth_path=config["paths"]["auth_config"]
        )
    except Exception as e:
        logger.critical(f"Failed to initialize modules: {e}")
        return

    # Configuration 
    BATCH_SIZE = config.get("batch", {}).get("size", 50)
    DELAY_SECONDS = config.get("batch", {}).get("delay_seconds", 2)
    MAX_RETRIES = config.get("batch", {}).get("max_retries", 3)
    MAX_TRACKS = config.get("batch", {}).get("max_tracks_to_process", 500)

    # 1. Sync Playlist (Source of Truth is now DB)
    logger.info("Step 1: Syncing Playlist (Live -> DB)...")
    tracks = scanner.sync_playlist(db)
    
    if not tracks:
        logger.error("No tracks found or sync failed. Exiting.")
        return

    logger.info(f"Sync complete. DB contains {len(tracks)} tracks.")

    # 2. Process Tracks via Spotify API
    logger.info("Step 2: Securing Audio Features via Spotify API...")
    processed_count = 0
    consecutive_failures = 0
    last_error_signature = None

    for i, track in enumerate(tracks):
        yt_id = track.get('yt_id')
        title = track.get('title')
        status = track.get('status')
        error_type = track.get('error_type')
        retry_count = track.get('retry_count') or 0

        # Attempt to get artist from DB JSON if available
        artist = ""
        artists_list = track.get('artist', [])
        if artists_list and isinstance(artists_list, list):
            artist = artists_list[0].get('name', '') if isinstance(artists_list[0], dict) else artists_list[0]

        if not yt_id or not title:
            continue

        # Skip permanently failed tracks
        if status == 'failed' and error_type == 'permanent':
            logger.info(f"[{i+1}/{len(tracks)}] Skipping '{title}' (Permanent failure: {error_type})")
            continue

        # Skip tracks that exceeded max retries
        if status == 'failed' and retry_count >= MAX_RETRIES:
            logger.info(f"[{i+1}/{len(tracks)}] Skipping '{title}' (Max retries reached: {retry_count})")
            continue

        # Skip already analyzed tracks
        if status == 'success':
            bpm = track.get('bpm')
            logger.info(f"[{i+1}/{len(tracks)}] Skipping '{title}' (Already analyzed). BPM: {bpm}")
            continue
        elif status == 'failed':
            logger.info(f"[{i+1}/{len(tracks)}] Re-trying failed track: '{title}' (retry {retry_count + 1}/{MAX_RETRIES})")
        
        # Check execution limit before processing
        if MAX_TRACKS > 0 and processed_count >= MAX_TRACKS:
            logger.info(f"🛑 Reached execution limit of {MAX_TRACKS} tracks. Stopping batch processing.")
            break

        # Circuit Breaker: abort if too many consecutive failures
        if consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
            logger.critical(
                f"🛑 CIRCUIT BREAKER: {consecutive_failures} consecutive failures detected. "
                f"Last error: {last_error_signature[:120] if last_error_signature else 'unknown'}. "
                f"Aborting to prevent resource waste. Fix the issue and retry."
            )
            break

        logger.info(f"[{i+1}/{len(tracks)}] Processing: {title} by {artist}...")

        # Search & Extract Features from Spotify
        try:
            algo_res = analyzer.analyze_track(title=title, artist=artist)
            
            # Update DB with Analysis
            db.update_analysis(
                yt_id=yt_id, 
                bpm=algo_res['bpm'], 
                key=algo_res['key'], 
                energy=algo_res['energy_rms'], 
                duration=algo_res['duration'],
                danceability=algo_res.get('danceability'),
                valence=algo_res.get('valence'),
                spotify_id=algo_res.get('spotify_id')
            )
            logger.info(f"  -> Success! BPM: {algo_res['bpm']}, Key: {algo_res['key']}, Energy: {algo_res['energy_rms']}")
            processed_count += 1
            
            # Reset circuit breaker on success
            consecutive_failures = 0
            last_error_signature = None

            # Small gentle delay between calls to be nice to the API
            time.sleep(DELAY_SECONDS)

        except ValueError as ve:
            # Not found on Spotify is a permanent semantic error for this track
            logger.warning(f"  -> Failed (Not Found on Spotify): {ve}")
            db.mark_failed(yt_id, error_type="permanent")
            
        except Exception as e:
            err_type = classify_error(e)
            error_sig = str(e)[:200]
            
            # Log specific Spotify rate limit backoffs
            if "429" in error_sig:
                logger.warning(f"  -> Rate Limited (HTTP 429). Spotipy handles backoff, but pausing loop.")
            else:
                logger.error(f"  -> Failed ({err_type}): {error_sig}")

            db.mark_failed(yt_id, error_type=err_type)
            
            # Track consecutive failures for circuit breaker
            consecutive_failures += 1
            last_error_signature = error_sig
            
            # Brief delay between failed attempts
            delay = min(2 ** consecutive_failures, 30)  
            if consecutive_failures > 1:
                logger.info(f"  -> Backoff delay: {delay}s (consecutive failures: {consecutive_failures})")
                time.sleep(delay)
        
        # Batch Delay (Safety Net for API usage chunks)
        if processed_count > 0 and processed_count % BATCH_SIZE == 0:
             logger.info(f"Batch limit reached ({BATCH_SIZE}). Cooldown for 10s...")
             time.sleep(10)

    # Summary
    logger.info("=" * 60)
    logger.info(f"Pipeline complete. Processed: {processed_count} tracks successfully.")
    if consecutive_failures > 0:
        logger.warning(f"Ended with {consecutive_failures} consecutive failures.")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
