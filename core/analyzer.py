import os
import re
import logging
import requests
import time
from difflib import SequenceMatcher
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Regex to clean YouTube-style suffixes from titles
_CLEAN_RE = re.compile(
    r"\s*[\(\[\{]?\s*("
    r"official\s*(music\s*)?video|"
    r"official\s*audio|"
    r"lyric\s*video|"
    r"audio\s*oficial|"
    r"video\s*oficial|"
    r"lyrics?|"
    r"hd|hq|4k|remaster(ed)?|"
    r"extended\s*(mix|version)?|"
    r"original\s*mix|"
    r"ft\.?\s*.+|"
    r"feat\.?\s*.+"
    r")\s*[\)\]\}]?\s*$",
    re.IGNORECASE
)


class AudioAnalyzer:
    """
    Analyzes audio features using the GetSongBPM REST API.
    Searches by title+artist, validates match quality, and extracts
    BPM, Key, Danceability from inline search results.
    """

    def __init__(self, config=None):
        if config is None:
            config = {}

        self.api_key = os.getenv("GETSONGBPM_API_KEY")
        if not self.api_key or self.api_key == "your_api_key_here":
            raise ValueError("GETSONGBPM_API_KEY must be set in .env")

        self.base_url = config.get("base_url", "https://api.getsong.co")
        self.match_threshold = config.get("match_threshold", 0.65)
        self.rate_limit_rpm = config.get("rate_limit_rpm", 50)
        self._min_interval = 60.0 / self.rate_limit_rpm
        self._last_request_time = 0

        logger.info(f"GetSongBPM Analyzer initialized (threshold={self.match_threshold})")

    # ── Rate Limiter ──────────────────────────
    def _throttle(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    # ── Query Cleaning ────────────────────────
    @staticmethod
    def _clean_title(title: str) -> str:
        """Remove YouTube-style suffixes like (Official Video), [Lyrics], etc."""
        cleaned = _CLEAN_RE.sub("", title).strip()
        cleaned = re.sub(r"\s*-\s*$", "", cleaned)
        return cleaned if cleaned else title

    # ── API Call ──────────────────────────────
    def _search_api(self, query: str) -> list:
        """Call GetSongBPM search endpoint. Returns list of song results."""
        self._throttle()
        url = f"{self.base_url}/search/"
        params = {
            "api_key": self.api_key,
            "type": "song",
            "lookup": query,
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            search_results = data.get("search", [])
            # API may return a string (e.g. error message) instead of list
            if not isinstance(search_results, list):
                return []
            # Filter out non-dict items
            return [r for r in search_results if isinstance(r, dict)]
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                logger.warning("GetSongBPM rate limit hit (429). Backing off 60s.")
                time.sleep(60)
                return self._search_api(query)
            raise
        except Exception as e:
            logger.error(f"GetSongBPM API error: {e}")
            raise

    # ── Match Scoring ─────────────────────────
    def _score_match(self, query: str, result: dict) -> float:
        """Calculate string similarity between query and API result title+artist."""
        result_title = result.get("title", "").lower()
        # Artist can be a dict with 'name' key or a string
        artist_data = result.get("artist", "")
        if isinstance(artist_data, dict):
            result_artist = artist_data.get("name", "").lower()
        else:
            result_artist = str(artist_data).lower()
        result_str = f"{result_title} {result_artist}".strip()
        query_lower = query.lower()
        return SequenceMatcher(None, query_lower, result_str).ratio()

    # ── High-Level Orchestrator ───────────────
    def analyze_track(self, title: str, artist: str = "") -> dict:
        """
        Search GetSongBPM for a track, validate match quality,
        and return BPM + Key + Danceability in a standardized dict.

        The GetSongBPM API returns tempo, key_of, open_key, danceability,
        and acousticness directly in the search results (no second call needed).

        Raises ValueError if no adequate match is found.
        """
        clean_title = self._clean_title(title)

        # Strategy 1: title + artist
        query = f"{clean_title} {artist}".strip() if artist else clean_title
        logger.info(f"  -> Searching GetSongBPM: '{query}'")
        results = self._search_api(query)

        # Strategy 2: fallback to title only if no results with artist
        if not results and artist:
            logger.info(f"  -> Fallback search (title only): '{clean_title}'")
            results = self._search_api(clean_title)

        if not results:
            raise ValueError(f"No results on GetSongBPM for '{query}'")

        # Score all results and pick best
        scored = []
        for r in results:
            score = self._score_match(query, r)
            scored.append((score, r))
        scored.sort(key=lambda x: x[0], reverse=True)

        best_score, best_match = scored[0]
        matched_title = best_match.get("title", "?")
        artist_data = best_match.get("artist", "")
        if isinstance(artist_data, dict):
            matched_artist = artist_data.get("name", "?")
        else:
            matched_artist = str(artist_data)

        logger.info(f"  -> Best match: '{matched_title}' by {matched_artist} (score: {best_score:.2f})")

        if best_score < self.match_threshold:
            raise ValueError(
                f"Match score {best_score:.2f} below threshold {self.match_threshold} "
                f"for '{query}' → '{matched_title}' by {matched_artist}"
            )

        # Extract features directly from search result
        tempo_str = best_match.get("tempo")
        key_of = best_match.get("key_of", "Unknown")
        time_sig = best_match.get("time_sig")
        danceability_raw = best_match.get("danceability")

        bpm = int(round(float(tempo_str))) if tempo_str else None
        # Normalize danceability from 0-100 range to 0.0-1.0
        danceability = round(danceability_raw / 100.0, 3) if danceability_raw is not None else None

        result = {
            "bpm": bpm,
            "key": key_of if key_of else "Unknown",
            "energy_rms": None,
            "duration": None,
            "danceability": danceability,
            "valence": None,
            "spotify_id": None,
            "match_score": round(best_score, 3),
            "time_sig": time_sig,
            "source": "getsongbpm",
        }

        return result
