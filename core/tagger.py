"""
SIROCO Semantic Tagger
Uses Gemini Flash to classify tracks into genre, mood, demographic,
energy_level and time_of_day tags from title + artist + audio features.
"""

import os
import json
import logging
import time
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Prompt Template ───────────────────────────
_SYSTEM_PROMPT = """You are a music classification expert. Given a song's metadata, 
classify it using ONLY the allowed values below. Return valid JSON only.

ALLOWED VALUES:
- genre (pick 1-2): rock, metal, punk, alternative, pop, indie-pop, synth-pop, 
  hip-hop, rap, trap, latin, reggaeton, salsa, bachata, cumbia, vallenato, merengue,
  electronic, house, techno, trance, jazz, blues, soul, funk, r&b,
  folk, acoustic, country, classical, ambient, ska, reggae, world
- mood (pick 1-2): dance, sing, chill, energize, romantic, melancholy, party, focus
- demographic (pick 1-2): solo, couple, family, social, workout
- energy_level (pick 1): low, medium, high
- time_of_day (pick 1-2): morning, afternoon, evening, night

RULES:
- Return ONLY a JSON object, no markdown, no explanation, no backticks.
- All values must be arrays of strings, except energy_level which is a single string.
- Use lowercase only.
"""

_TRACK_TEMPLATE = """Song: "{title}"
Artist: "{artist}"
BPM: {bpm}
Key: {key}
Danceability: {danceability}"""

_BATCH_TEMPLATE = """Classify each of these {count} songs. Return a JSON array with one object per song, in the same order.

{tracks}"""


class SirocoTagger:
    """
    Classifies tracks using Gemini Flash API.
    Supports single-track and batch classification.
    """

    def __init__(self, config=None):
        if config is None:
            config = {}

        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be set in .env")

        self.batch_size = config.get("batch_size", 10)
        self.model_name = config.get("model", "gemini-2.0-flash")

        # Import and configure
        from google import genai
        self._client = genai.Client(api_key=self.api_key)

        logger.info(f"SirocoTagger initialized (model={self.model_name}, batch={self.batch_size})")

    def _call_gemini(self, prompt: str) -> str:
        """Send prompt to Gemini and return raw text response."""
        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "system_instruction": _SYSTEM_PROMPT,
                    "temperature": 0.1,
                    "max_output_tokens": 2048,
                }
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    def _parse_response(self, raw: str) -> list:
        """Parse Gemini response into list of tag dicts."""
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            # Remove ```json and trailing ```
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini output: {e}\nRaw: {cleaned[:500]}")
            raise ValueError(f"Invalid JSON from Gemini: {e}")

        # Normalize: if single dict, wrap in list
        if isinstance(parsed, dict):
            parsed = [parsed]

        if not isinstance(parsed, list):
            raise ValueError(f"Expected list or dict, got {type(parsed)}")

        return parsed

    def _validate_tags(self, tags: dict) -> dict:
        """Ensure tag values are valid; fill missing with defaults."""
        valid_genres = {"rock","metal","punk","alternative","pop","indie-pop","synth-pop",
            "hip-hop","rap","trap","latin","reggaeton","salsa","bachata","cumbia",
            "vallenato","merengue","electronic","house","techno","trance","jazz",
            "blues","soul","funk","r&b","folk","acoustic","country","classical",
            "ambient","ska","reggae","world"}
        valid_moods = {"dance","sing","chill","energize","romantic","melancholy","party","focus"}
        valid_demo = {"solo","couple","family","social","workout"}
        valid_energy = {"low","medium","high"}
        valid_time = {"morning","afternoon","evening","night"}

        def filter_list(values, allowed):
            if not isinstance(values, list):
                values = [values] if isinstance(values, str) else []
            return [v.lower().strip() for v in values if v.lower().strip() in allowed]

        result = {
            "genre": filter_list(tags.get("genre", []), valid_genres) or ["unknown"],
            "mood": filter_list(tags.get("mood", []), valid_moods) or ["chill"],
            "demographic": filter_list(tags.get("demographic", []), valid_demo) or ["solo"],
            "energy_level": tags.get("energy_level", "medium"),
            "time_of_day": filter_list(tags.get("time_of_day", []), valid_time) or ["afternoon"],
        }

        if result["energy_level"] not in valid_energy:
            result["energy_level"] = "medium"

        return result

    def classify_track(self, title: str, artist: str, bpm=None, key=None, danceability=None) -> dict:
        """Classify a single track. Returns validated tag dict."""
        prompt = _TRACK_TEMPLATE.format(
            title=title,
            artist=artist or "Unknown",
            bpm=bpm or "Unknown",
            key=key or "Unknown",
            danceability=danceability or "Unknown",
        )

        raw = self._call_gemini(prompt)
        parsed = self._parse_response(raw)
        if not parsed:
            raise ValueError(f"Empty response for '{title}'")
        return self._validate_tags(parsed[0])

    def classify_batch(self, tracks: list) -> list:
        """
        Classify a batch of tracks in a single API call.
        Each track should be a dict with: title, artist, bpm, key, danceability.
        Returns list of validated tag dicts in the same order.
        """
        track_descriptions = []
        for i, t in enumerate(tracks):
            desc = _TRACK_TEMPLATE.format(
                title=t.get("title", "?"),
                artist=t.get("artist", "Unknown"),
                bpm=t.get("bpm", "Unknown"),
                key=t.get("key", "Unknown"),
                danceability=t.get("danceability", "Unknown"),
            )
            track_descriptions.append(f"[{i+1}]\n{desc}")

        prompt = _BATCH_TEMPLATE.format(
            count=len(tracks),
            tracks="\n\n".join(track_descriptions)
        )

        raw = self._call_gemini(prompt)
        parsed = self._parse_response(raw)

        # Validate each result
        results = []
        for i, tags in enumerate(parsed):
            validated = self._validate_tags(tags)
            results.append(validated)

        # Pad with defaults if response is shorter than input
        while len(results) < len(tracks):
            results.append(self._validate_tags({}))

        return results
