import os
import re
import logging
import requests
import time
from difflib import SequenceMatcher
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Title Preprocessing — Multi-pass cleaning
# ──────────────────────────────────────────────

# Pass 1: Remove bracketed/parenthesized suffixes (EN + ES + PT)
_BRACKET_RE = re.compile(
    r"\s*[\(\[\{]\s*("
    r"official\s*(music\s*)?video|official\s*audio|"
    r"lyric\s*video|lyrics?\s*video|"
    r"audio\s*oficial|video\s*oficial|video\s*cl[ií]p|videoclip|"
    r"lyrics?|letra(\s*\+\s*video)?|"
    r"hd|hq|4k|1080p|720p|"
    r"remaster(ed)?(\s*\d{4})?|"
    r"extended\s*(mix|version)?|original\s*mix|"
    r"live(\s+on\s+\w+)?|en\s+vivo|ao\s+vivo|directo|"
    r"ac[uú]stic[oa]?|unplugged|sinf[oó]nico|"
    r"version\s+original|versi[oó]n\s+original|"
    r"sub\s+esp|subtitulad[oa]|closed\s+caption(ed)?|"
    r"super\s+clean\s+version|clean\s+version|"
    r"ft\.?\s*.+|feat\.?\s*.+"
    r")\s*[\)\]\}]",
    re.IGNORECASE
)

# Pass 2: Remove trailing non-bracketed suffixes
_TRAILING_RE = re.compile(
    r"\s*[-–—]\s*("
    r"official\s*(music\s*)?video|official\s*audio|"
    r"lyric\s*video|lyrics?|"
    r"audio\s*oficial|video\s*oficial|"
    r"hd|hq|4k|remaster(ed)?|"
    r"live|en\s+vivo|ao\s+vivo|directo"
    r")\s*$",
    re.IGNORECASE
)

# Pass 3: Remove file extensions
_EXT_RE = re.compile(r"\.(flv|mp4|mp3|avi|webm|mkv|wav)\s*$", re.IGNORECASE)

# Pass 4: Remove year-only parenthetical like (1961), (2007), (2019 Mix)
_YEAR_RE = re.compile(r"\s*[\(\[]\s*\d{4}(\s*(mix|remaster))?\s*[\)\]]", re.IGNORECASE)

# Stopwords for core word extraction (EN + ES + PT)
_STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "or", "is",
    "de", "del", "la", "el", "las", "los", "en", "con", "por", "un", "una",
    "y", "o", "que", "se", "mi", "tu", "su", "al", "es",
    "do", "da", "dos", "das", "no", "na", "em", "um", "uma", "e",
}


class AudioAnalyzer:
    """
    Analyzes audio features using the GetSongBPM REST API.
    v2: Multi-pass title cleaning, dash-artist extraction,
    word-by-word fallback, and type=both search.
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

        logger.info(f"GetSongBPM Analyzer v2 initialized (threshold={self.match_threshold})")

    # ── Rate Limiter ──────────────────────────
    def _throttle(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    # ── Title Preprocessing v2 ────────────────

    @staticmethod
    def _clean_title(title: str) -> str:
        """
        Multi-pass title cleaning:
        1. Remove bracketed suffixes (EN/ES/PT)
        2. Remove trailing non-bracketed suffixes
        3. Remove file extensions
        4. Remove year-only parenthetical
        5. Strip whitespace
        """
        cleaned = title
        cleaned = _BRACKET_RE.sub("", cleaned)
        cleaned = _TRAILING_RE.sub("", cleaned)
        cleaned = _EXT_RE.sub("", cleaned)
        cleaned = _YEAR_RE.sub("", cleaned)
        cleaned = cleaned.strip()
        # Remove trailing dashes/colons left behind
        cleaned = re.sub(r"\s*[-–—:]\s*$", "", cleaned).strip()
        return cleaned if cleaned else title

    @staticmethod
    def _split_artist_title(title: str) -> tuple:
        """
        If the title contains 'Artist - Song' or 'Artist — Song' or 'Artist: Song',
        split and return (extracted_artist, extracted_title).
        Only splits on the FIRST separator. Returns (None, title) if no pattern found.
        """
        # Match patterns like "Andrés Calamaro - Crímenes perfectos"
        # but NOT "Song - Episodio 2" (numeric after dash is likely a subtitle)
        for sep in [" — ", " – ", " - ", ": "]:
            if sep in title:
                parts = title.split(sep, 1)
                left = parts[0].strip()
                right = parts[1].strip()
                # Heuristic: if left part is short (1-4 words) and right is longer,
                # left is likely the artist
                left_words = len(left.split())
                right_words = len(right.split())
                if 1 <= left_words <= 5 and right_words >= 1:
                    return (left, right)
        return (None, title)

    @staticmethod
    def _extract_core_words(title: str) -> str:
        """
        Extract the 2-3 most significant words from a title.
        Removes stopwords and keeps content words.
        Used as a last-resort search query.
        """
        words = re.findall(r"[a-záéíóúñüàèìòùâêîôûãõçA-Z]+", title)
        content_words = [w for w in words if w.lower() not in _STOPWORDS and len(w) > 1]
        # Take first 3 content words
        return " ".join(content_words[:3])

    # ── API Calls ─────────────────────────────

    def _search_api(self, query: str, search_type: str = "song") -> list:
        """Call GetSongBPM search endpoint. Returns list of song results."""
        self._throttle()
        url = f"{self.base_url}/search/"
        params = {
            "api_key": self.api_key,
            "type": search_type,
            "lookup": query,
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            search_results = data.get("search", [])
            if not isinstance(search_results, list):
                return []
            return [r for r in search_results if isinstance(r, dict)]
        except requests.exceptions.HTTPError:
            if resp.status_code == 429:
                logger.warning("GetSongBPM rate limit hit (429). Backing off 60s.")
                time.sleep(60)
                return self._search_api(query, search_type)
            raise
        except Exception as e:
            logger.error(f"GetSongBPM API error: {e}")
            raise

    def _search_both(self, title: str, artist: str) -> list:
        """
        Use the API's type=both mode with structured lookup:
        lookup=song:TITLE artist:ARTIST
        """
        self._throttle()
        url = f"{self.base_url}/search/"
        lookup = f"song:{title} artist:{artist}"
        params = {
            "api_key": self.api_key,
            "type": "both",
            "lookup": lookup,
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            search_results = data.get("search", [])
            if not isinstance(search_results, list):
                return []
            return [r for r in search_results if isinstance(r, dict)]
        except requests.exceptions.HTTPError:
            if resp.status_code == 429:
                logger.warning("GetSongBPM rate limit hit (429). Backing off 60s.")
                time.sleep(60)
                return self._search_both(title, artist)
            raise
        except Exception as e:
            logger.error(f"GetSongBPM API error (both): {e}")
            raise

    # ── Match Scoring ─────────────────────────
    def _score_match(self, query: str, result: dict) -> float:
        """Calculate string similarity between query and API result title+artist."""
        result_title = result.get("title", "").lower()
        artist_data = result.get("artist", "")
        if isinstance(artist_data, dict):
            result_artist = artist_data.get("name", "").lower()
        else:
            result_artist = str(artist_data).lower()
        result_str = f"{result_title} {result_artist}".strip()
        query_lower = query.lower()
        return SequenceMatcher(None, query_lower, result_str).ratio()

    def _pick_best(self, results: list, query: str) -> tuple:
        """Score all results and return (best_score, best_match) or (0, None)."""
        if not results:
            return (0, None)
        scored = []
        for r in results:
            score = self._score_match(query, r)
            scored.append((score, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0]

    # ── Artist Name Extraction ────────────────
    @staticmethod
    def _get_artist_name(result: dict) -> str:
        """Safely extract artist name from a search result."""
        artist_data = result.get("artist", "")
        if isinstance(artist_data, dict):
            return artist_data.get("name", "?")
        return str(artist_data) if artist_data else "?"

    # ── High-Level Orchestrator ───────────────
    def analyze_track(self, title: str, artist: str = "") -> dict:
        """
        Multi-strategy search on GetSongBPM:

        1. Clean title + YT artist (type=song)
        2. Clean title only (type=song)
        3. Extracted title from dash-split + extracted artist (type=both)
        4. Core words + artist (type=song)
        5. Core words only (type=song)

        Returns dict with BPM, Key, Danceability, match_score.
        Raises ValueError if no adequate match is found.
        """
        clean = self._clean_title(title)
        extracted_artist, extracted_title = self._split_artist_title(clean)
        core_words = self._extract_core_words(extracted_title or clean)

        # Determine best artist to use
        # If we extracted an artist from the title and the YT uploader looks different,
        # prefer the extracted one
        primary_artist = artist
        if extracted_artist:
            # Extracted artist is more reliable when present
            primary_artist = extracted_artist
            clean = extracted_title  # Use the song-part only

        strategies = []

        # Strategy 1: clean title + best artist (type=song)
        if primary_artist:
            q1 = f"{clean} {primary_artist}"
            strategies.append(("title+artist", q1, "song"))

        # Strategy 2: clean title only (type=song)
        strategies.append(("title_only", clean, "song"))

        # Strategy 3: type=both if we have a good artist
        if primary_artist and extracted_title:
            strategies.append(("type_both", f"{extracted_title}|{primary_artist}", "both"))

        # Strategy 4: core words + artist (type=song)
        if core_words and primary_artist:
            q4 = f"{core_words} {primary_artist}"
            if q4.lower() != clean.lower():
                strategies.append(("core+artist", q4, "song"))

        # Strategy 5: core words only (type=song)
        if core_words and core_words.lower() != clean.lower():
            strategies.append(("core_only", core_words, "song"))

        best_score = 0
        best_match = None
        best_query = ""
        best_strategy = ""

        for strategy_name, query, search_type in strategies:
            if best_score >= self.match_threshold:
                break  # Already found a good match

            logger.info(f"  -> [{strategy_name}] Searching: '{query}'")

            if search_type == "both" and "|" in query:
                parts = query.split("|", 1)
                results = self._search_both(parts[0], parts[1])
                query = f"{parts[0]} {parts[1]}"
            else:
                results = self._search_api(query, search_type)

            if not results:
                continue

            score, match = self._pick_best(results, query)
            if score > best_score:
                best_score = score
                best_match = match
                best_query = query
                best_strategy = strategy_name

        if not best_match:
            raise ValueError(f"No results on GetSongBPM for '{title}'")

        matched_title = best_match.get("title", "?")
        matched_artist = self._get_artist_name(best_match)

        logger.info(
            f"  -> Best [{best_strategy}]: '{matched_title}' by {matched_artist} "
            f"(score: {best_score:.2f})"
        )

        if best_score < self.match_threshold:
            raise ValueError(
                f"Match score {best_score:.2f} below threshold {self.match_threshold} "
                f"for '{title}' → '{matched_title}' by {matched_artist}"
            )

        # Extract features directly from search result
        tempo_str = best_match.get("tempo")
        key_of = best_match.get("key_of", "Unknown")
        time_sig = best_match.get("time_sig")
        danceability_raw = best_match.get("danceability")

        bpm = int(round(float(tempo_str))) if tempo_str else None
        danceability = round(danceability_raw / 100.0, 3) if danceability_raw is not None else None

        return {
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
