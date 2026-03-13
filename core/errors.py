"""
SIROCO Error Classifier
Categorizes API, network, and scraping exceptions into actionable types.
"""

import re
import logging

logger = logging.getLogger(__name__)

# Patterns that indicate PERMANENT failures (never retry)
_PERMANENT_PATTERNS = [
    r"copyright",
    r"blocked",
    r"video.*(?:unavailable|removed|deleted|private)",
    r"this video is not available",
    r"sign in to confirm your age",
    r"account.*required",
    r"members.only",
    r"premiere",
    r"join this channel",
    r"HTTP Error 404",
    r"HTTP Error 410",
    # GetSongBPM specific
    r"No results on GetSongBPM",
    r"Match score .+ below threshold",
    r"Track not found",
]

# Patterns that indicate TRANSIENT failures (safe to retry)
_TRANSIENT_PATTERNS = [
    r"HTTP Error 403",
    r"HTTP Error 429",
    r"HTTP Error 5\d{2}",
    r"timed?\s*out",
    r"connection.*(?:reset|refused|aborted|error)",
    r"network",
    r"temporary",
    r"urlopen error",
    r"incomplete read",
    r"ssl",
    r"socket",
    r"too many requests",
    r"rate limit",
]

_permanent_re = re.compile("|".join(_PERMANENT_PATTERNS), re.IGNORECASE)
_transient_re = re.compile("|".join(_TRANSIENT_PATTERNS), re.IGNORECASE)


def classify_error(exception: Exception) -> str:
    """
    Classify an exception from yt-dlp / network operations.

    Returns:
        "permanent"  — Do NOT retry (copyright, geo-block, removed video).
        "transient"  — Safe to retry (timeout, rate limit, server error).
        "unknown"    — Unrecognized error; treated as transient with caution.
    """
    message = str(exception)

    # Check permanent first (more specific)
    if _permanent_re.search(message):
        logger.info(f"Error classified as PERMANENT: {message[:120]}")
        return "permanent"

    if _transient_re.search(message):
        logger.info(f"Error classified as TRANSIENT: {message[:120]}")
        return "transient"

    logger.warning(f"Error classified as UNKNOWN: {message[:120]}")
    return "unknown"
