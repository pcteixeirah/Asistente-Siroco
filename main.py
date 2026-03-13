import os
import sys
import time
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

    parser = argparse.ArgumentParser(description="Siroco Musical Analysis Workflow (GetSongBPM API)")
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
        analyzer = AudioAnalyzer(config=config.get("getsongbpm", {}))
        scanner = PlaylistScanner(
            playlist_id=args.playlist,
            auth_path=config["paths"]["auth_config"]
        )
    except Exception as e:
        logger.critical(f"Failed to initialize modules: {e}")
        return

    # Batch Configuration
    BATCH_SIZE = config.get("batch", {}).get("size", 50)
    MAX_RETRIES = config.get("batch", {}).get("max_retries", 3)
    MAX_TRACKS = config.get("batch", {}).get("max_tracks_to_process", 0)

    # 1. Sync Playlist (Source of Truth is now DB)
    logger.info("Step 1: Syncing Playlist (Live -> DB)...")
    tracks = scanner.sync_playlist(db)
    
    if not tracks:
        logger.error("No tracks found or sync failed. Exiting.")
        return

    logger.info(f"Sync complete. DB contains {len(tracks)} tracks.")

    # 2. Process Tracks via GetSongBPM API
    logger.info("Step 2: Resolving Audio Features via GetSongBPM API...")
    processed_count = 0
    not_found_count = 0
    consecutive_failures = 0
    last_error_signature = None

    for i, track in enumerate(tracks):
        yt_id = track.get('yt_id')
        title = track.get('title')
        status = track.get('status')
        error_type = track.get('error_type')
        retry_count = track.get('retry_count') or 0

        # Get artist string from DB JSON
        artist = ""
        artists_data = track.get('artist', [])
        if artists_data and isinstance(artists_data, list):
            first = artists_data[0]
            artist = first.get('name', '') if isinstance(first, dict) else str(first)

        if not yt_id or not title:
            continue

        # Skip permanently failed tracks
        if status == 'failed' and error_type == 'permanent':
            logger.info(f"[{i+1}/{len(tracks)}] Skipping '{title}' (Permanent failure)")
            continue

        # Skip tracks that exceeded max retries
        if status == 'failed' and retry_count >= MAX_RETRIES:
            logger.info(f"[{i+1}/{len(tracks)}] Skipping '{title}' (Max retries: {retry_count})")
            continue

        # Skip already analyzed tracks
        if status == 'success':
            bpm = track.get('bpm')
            logger.info(f"[{i+1}/{len(tracks)}] Skipping '{title}' (Already analyzed). BPM: {bpm}")
            continue
        elif status == 'failed':
            logger.info(f"[{i+1}/{len(tracks)}] Re-trying failed track: '{title}' (retry {retry_count + 1}/{MAX_RETRIES})")
        
        # Check execution limit
        if MAX_TRACKS > 0 and processed_count >= MAX_TRACKS:
            logger.info(f"🛑 Reached execution limit of {MAX_TRACKS} tracks.")
            break

        # Circuit Breaker
        if consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
            logger.critical(
                f"🛑 CIRCUIT BREAKER: {consecutive_failures} consecutive failures. "
                f"Last error: {last_error_signature[:120] if last_error_signature else 'unknown'}. Aborting."
            )
            break

        logger.info(f"[{i+1}/{len(tracks)}] Processing: {title}...")

        # Search & Extract Features from GetSongBPM
        try:
            algo_res = analyzer.analyze_track(title=title, artist=artist)
            
            db.update_analysis(
                yt_id=yt_id, 
                bpm=algo_res['bpm'], 
                key=algo_res['key'], 
                energy=algo_res.get('energy_rms'),
                duration=algo_res.get('duration'),
                danceability=algo_res.get('danceability'),
                valence=algo_res.get('valence'),
                match_score=algo_res.get('match_score'),
            )
            logger.info(f"  -> ✅ BPM: {algo_res['bpm']}, Key: {algo_res['key']}, Match: {algo_res.get('match_score', '?')}")
            processed_count += 1
            
            # Reset circuit breaker on success
            consecutive_failures = 0
            last_error_signature = None

        except ValueError as ve:
            # Not found on GetSongBPM → permanent
            logger.warning(f"  -> ⚠️ Not Found: {ve}")
            db.mark_failed(yt_id, error_type="permanent")
            not_found_count += 1
            
        except Exception as e:
            err_type = classify_error(e)
            error_sig = str(e)[:200]
            logger.error(f"  -> ❌ Failed ({err_type}): {error_sig}")
            db.mark_failed(yt_id, error_type=err_type)
            
            consecutive_failures += 1
            last_error_signature = error_sig
            
            delay = min(2 ** consecutive_failures, 30)  
            if consecutive_failures > 1:
                logger.info(f"  -> Backoff delay: {delay}s (consecutive failures: {consecutive_failures})")
                time.sleep(delay)

    # Summary
    logger.info("=" * 60)
    logger.info(f"Pipeline complete.")
    logger.info(f"  Analyzed successfully: {processed_count}")
    logger.info(f"  Not found on GetSongBPM: {not_found_count}")
    if consecutive_failures > 0:
        logger.warning(f"  Ended with {consecutive_failures} consecutive failures.")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
