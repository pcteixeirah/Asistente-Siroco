import os
import sys
import time
import random
import logging
import argparse
from core.config import load_config
from core.errors import classify_error
from core.database import SirocoRegistry
from core.downloader import LowFiDownloader
from core.proxy_pool import ProxyPool
from core.analyzer import AudioAnalyzer
from core.scanner import PlaylistScanner

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

    parser = argparse.ArgumentParser(description="Siroco Musical Analysis Proxy")
    parser.add_argument(
        "--playlist", type=str,
        default=config["playlist"]["default_id"],
        help="YouTube Playlist ID"
    )
    args = parser.parse_args()

    logger.info(f"Starting Proxy Workflow for Playlist ID: {args.playlist}")

    # Initialize Modules (all receive config values)
    try:
        proxy_pool = ProxyPool(config.get("proxy_rotation", {}))
        
        db = SirocoRegistry(db_path=config["paths"]["database"])
        downloader = LowFiDownloader(
            download_path=config["paths"]["temp_cache"],
            audio_format=config["downloader"]["format"],
            proxy_pool=proxy_pool,
            cookies_path=config["paths"].get("cookies")
        )
        analyzer = AudioAnalyzer(sample_rate=config["analyzer"]["sample_rate"])
        scanner = PlaylistScanner(
            playlist_id=args.playlist,
            auth_path=config["paths"]["auth_config"]
        )
    except Exception as e:
        logger.critical(f"Failed to initialize modules: {e}")
        return

    # Proxy config
    BATCH_SIZE = config["proxy"]["batch_size"]
    DELAY_MIN = config["proxy"]["batch_delay_min"]
    DELAY_MAX = config["proxy"]["batch_delay_max"]
    MAX_RETRIES = config["proxy"]["max_retries"]
    MAX_TRACKS = config["proxy"].get("max_tracks_to_process", 0)

    # 1. Sync Playlist (Source of Truth is now DB)
    logger.info("Step 1: Syncing Playlist (Live -> DB)...")
    tracks = scanner.sync_playlist(db)
    
    if not tracks:
        logger.error("No tracks found or sync failed. Exiting.")
        return

    logger.info(f"Sync complete. DB contains {len(tracks)} tracks.")

    # 2. Process Tracks
    logger.info("Step 2: Processing Tracks (Download -> Analyze -> Store)...")
    processed_count = 0

    for i, track in enumerate(tracks):
        yt_id = track.get('yt_id')
        title = track.get('title')
        status = track.get('status')
        error_type = track.get('error_type')
        retry_count = track.get('retry_count') or 0

        if not yt_id:
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

        logger.info(f"[{i+1}/{len(tracks)}] Processing: {title}...")

        # Download & Analyze
        try:
            # Download
            logger.info("  -> Downloading...")
            audio_path = downloader.download_audio(yt_id)
            
            # Analyze
            logger.info("  -> Analyzing...")
            algo_res = analyzer.analyze_track(audio_path)
            
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
            err_type = classify_error(e)
            if err_type == "transient":
                proxy_pool.rotate()
                logger.info(f"  -> Rotated proxy (Active: {proxy_pool.get_proxy()})")
            
            logger.error(f"  -> Failed ({err_type}): {e}")
            db.mark_failed(yt_id, error_type=err_type)
        
        # Batch Delay to avoid rate limiting
        if processed_count > 0 and processed_count % BATCH_SIZE == 0:
             wait_time = random.randint(DELAY_MIN, DELAY_MAX)
             logger.info(f"Batch limit reached. Sleeping {wait_time}s...")
             time.sleep(wait_time)

if __name__ == "__main__":
    main()
