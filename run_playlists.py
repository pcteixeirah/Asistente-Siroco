"""
SIROCO Playlist Runner
Generates YouTube Music playlists based on schedule defined in config.yaml
and LLM semantic tags from the database.
"""

import os
import sys
import logging
import argparse
from core.config import load_config
from core.playlist_generator import PlaylistGenerator

def main():
    parser = argparse.ArgumentParser(description="Generate YT Music Playlists from SIROCO data.")
    parser.add_argument("--timeslot", type=str, help="Specific timeslot to generate (morning, afternoon, evening, night). If omitted, generates all.")
    args = parser.parse_args()

    config = load_config()

    # Setup logging
    log_dir = os.path.dirname(config["paths"]["log_file"])
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config["paths"]["log_file"], encoding='utf-8', mode='a'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logger = logging.getLogger("PlaylistRunner")

    # Initialize generator
    db_path = config["paths"]["database"]
    auth_cfg = config["paths"].get("auth_config", "setup/headers_auth.cfg")
    schedule = config.get("schedule", {})

    generator = PlaylistGenerator(db_path=db_path, auth_cfg=auth_cfg, schedule_config=schedule)
    
    if not generator.yt:
        logger.error("YTMusic authentication blocked the process. Exiting.")
        return

    timeslots = [args.timeslot] if args.timeslot else ["morning", "afternoon", "evening", "night"]

    logger.info("="*60)
    logger.info(f" SIROCO Playlist Generation Started")
    logger.info("="*60)

    for ts in timeslots:
        if ts not in schedule:
            logger.warning(f"Skipping unknown timeslot: {ts}")
            continue
            
        logger.info(f"--- Processing timeslot: {ts.upper()} ---")
        tracks = generator.generate_for_timeslot(ts)
        
        if not tracks:
            logger.warning(f"No tracks found for {ts}. Skipping.")
            continue
            
        playlist_name = f"Siroco: {ts.capitalize()} Mix"
        desc = f"SIROCO Auto-generated Mix for {ts.capitalize()} ({schedule[ts]}). Semantic matching using AI."
        
        generator.publish_to_ytmusic(playlist_name=playlist_name, tracks=tracks, description=desc)

    logger.info("="*60)
    logger.info(" All defined playlists have been processed.")
    logger.info("="*60)


if __name__ == "__main__":
    main()
