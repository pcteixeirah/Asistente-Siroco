"""
SIROCO Test Suite — GetSongBPM Analyzer
Tests the core/analyzer.py module against the live GetSongBPM API.
Run: venv/Scripts/python.exe -m pytest tests/test_getsongbpm_analyzer.py -v
"""

import os
import sys
import time
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.analyzer import AudioAnalyzer


# ─── Fixtures ──────────────────────────────────

@pytest.fixture(scope="module")
def analyzer():
    """Initialize analyzer once for all tests in the module."""
    return AudioAnalyzer()


# ─── Test 1: Initialization ───────────────────

class TestInitialization:
    def test_api_key_loaded(self, analyzer):
        """API key must be present and valid."""
        assert analyzer.api_key is not None
        assert len(analyzer.api_key) > 10

    def test_config_defaults(self, analyzer):
        """Verify defaults are sane."""
        assert analyzer.match_threshold > 0
        assert analyzer.match_threshold < 1
        assert analyzer.rate_limit_rpm > 0
        assert "getsong.co" in analyzer.base_url


# ─── Test 2: Known Track Search ───────────────

class TestKnownTrackSearch:
    def test_despacito(self, analyzer):
        """'Despacito' by Luis Fonsi — very mainstream Latin track."""
        time.sleep(2)  # Respect rate limits
        result = analyzer.analyze_track(title="Despacito", artist="Luis Fonsi")
        assert result is not None
        assert result["bpm"] is not None
        assert 80 <= result["bpm"] <= 100, f"BPM {result['bpm']} out of expected range"
        assert result["key"] != "Unknown"
        assert result["match_score"] >= 0.5
        assert result["source"] == "getsongbpm"
        # GetSongBPM returns danceability inline
        assert result["danceability"] is not None
        assert 0.0 <= result["danceability"] <= 1.0


# ─── Test 3: Title Cleaning ──────────────────

class TestTitleCleaning:
    def test_removes_official_video(self):
        cleaned = AudioAnalyzer._clean_title("Poker Face (Official Music Video)")
        assert "Official" not in cleaned
        assert "Poker Face" in cleaned

    def test_removes_lyrics_tag(self):
        cleaned = AudioAnalyzer._clean_title("Shape of You [Lyrics]")
        assert "Lyrics" not in cleaned
        assert "Shape of You" in cleaned

    def test_removes_audio_oficial(self):
        cleaned = AudioAnalyzer._clean_title("Despacito (Audio Oficial)")
        assert "Audio" not in cleaned
        assert "Despacito" in cleaned

    def test_preserves_clean_title(self):
        cleaned = AudioAnalyzer._clean_title("Bohemian Rhapsody")
        assert cleaned == "Bohemian Rhapsody"


# ─── Test 4: Match Threshold Rejection ───────

class TestMatchThreshold:
    def test_nonsense_query_raises(self, analyzer):
        """A completely random string should not match any track."""
        time.sleep(2)
        with pytest.raises((ValueError, Exception)):
            analyzer.analyze_track(title="xyzqwert8837nonsense", artist="")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
