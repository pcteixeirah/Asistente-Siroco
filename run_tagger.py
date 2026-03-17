"""
SIROCO Tag Runner — Batch classification using Gemini Flash
Usage: venv/Scripts/python.exe run_tagger.py
"""

import os
import sys
import logging
import time
from core.config import load_config
from core.database import SirocoRegistry
from core.tagger import SirocoTagger


def main():
    config = load_config()

    # Setup logging
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

    # Initialize
    db = SirocoRegistry(db_path=config["paths"]["database"])
    tagger = SirocoTagger(config=config.get("tagger", {}))

    # Get untagged tracks
    tracks = db.get_tracks_for_tagging()
    logger.info(f"Found {len(tracks)} tracks to classify.")

    if not tracks:
        logger.info("All tracks already tagged. Nothing to do.")
        return

    batch_size = config.get("tagger", {}).get("batch_size", 10)
    total_tagged = 0
    total_errors = 0

    for i in range(0, len(tracks), batch_size):
        batch = tracks[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(tracks) + batch_size - 1) // batch_size

        logger.info(f"=== Batch {batch_num}/{total_batches} ({len(batch)} tracks) ===")

        try:
            results = tagger.classify_batch(batch)

            for track, tags in zip(batch, results):
                success = db.update_tags(
                    yt_id=track["yt_id"],
                    genre=tags["genre"],
                    mood=tags["mood"],
                    demographic=tags["demographic"],
                    energy_level=tags["energy_level"],
                    time_of_day=tags["time_of_day"],
                )
                if success:
                    total_tagged += 1
                    logger.info(
                        f"  ✅ {track['title'][:45]:45s} | "
                        f"genre={tags['genre']} mood={tags['mood']} "
                        f"energy={tags['energy_level']}"
                    )
                else:
                    total_errors += 1

        except Exception as e:
            logger.error(f"  ❌ Batch {batch_num} failed: {e}")
            total_errors += len(batch)
            # Wait before retrying to avoid burning API quota
            time.sleep(5)

        # Small delay between batches to be polite
        time.sleep(1)

    logger.info("=" * 60)
    logger.info(f"Tagging complete.")
    logger.info(f"  Tagged successfully: {total_tagged}")
    logger.info(f"  Errors: {total_errors}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
