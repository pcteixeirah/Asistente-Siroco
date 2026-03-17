"""
SIROCO Test Suite — GetSongBPM Analyzer v2
Tests multi-pass title cleaning, artist extraction, and live API search.
Run: venv/Scripts/python.exe -m pytest tests/test_getsongbpm_analyzer.py -v
"""

import os
import sys
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.analyzer import AudioAnalyzer


@pytest.fixture(scope="module")
def analyzer():
    return AudioAnalyzer()


# ─── Test 1: Initialization ───────────────────

class TestInitialization:
    def test_api_key_loaded(self, analyzer):
        assert analyzer.api_key is not None
        assert len(analyzer.api_key) > 10

    def test_config_defaults(self, analyzer):
        assert 0 < analyzer.match_threshold < 1
        assert analyzer.rate_limit_rpm > 0
        assert "getsong.co" in analyzer.base_url


# ─── Test 2: Title Cleaning v2 ───────────────

class TestTitleCleaningV2:
    def test_removes_official_video(self):
        assert "Poker Face" in AudioAnalyzer._clean_title("Poker Face (Official Music Video)")

    def test_removes_lyrics_bracket(self):
        assert "Shape of You" in AudioAnalyzer._clean_title("Shape of You [Lyrics]")

    def test_removes_audio_oficial(self):
        assert "Despacito" in AudioAnalyzer._clean_title("Despacito (Audio Oficial)")

    def test_removes_ao_vivo(self):
        cleaned = AudioAnalyzer._clean_title("Ai Se Eu Te Pego (Ao Vivo)")
        assert "Ai Se Eu Te Pego" in cleaned
        assert "Ao Vivo" not in cleaned

    def test_removes_directo(self):
        cleaned = AudioAnalyzer._clean_title("19 Dias y 500 Noches (Directo)")
        assert "19 Dias y 500 Noches" in cleaned
        assert "Directo" not in cleaned

    def test_removes_4k_video(self):
        cleaned = AudioAnalyzer._clean_title("Back In Black (Official 4K Video)")
        assert "Back In Black" in cleaned

    def test_removes_file_extension(self):
        cleaned = AudioAnalyzer._clean_title("La Parte De Adelante.flv")
        assert ".flv" not in cleaned

    def test_removes_year_parenthetical(self):
        cleaned = AudioAnalyzer._clean_title("Big Poppa (2007 Remaster)")
        assert "Big Poppa" in cleaned
        assert "2007" not in cleaned

    def test_removes_letra_video(self):
        cleaned = AudioAnalyzer._clean_title("Stand By Me [Letra + Video]")
        assert "Stand By Me" in cleaned
        assert "Letra" not in cleaned

    def test_removes_videoclip(self):
        cleaned = AudioAnalyzer._clean_title("El solitario (videoclip) (feat. David Hidalgo)")
        assert "solitario" in cleaned

    def test_preserves_clean_title(self):
        assert AudioAnalyzer._clean_title("Bohemian Rhapsody") == "Bohemian Rhapsody"


# ─── Test 3: Artist-Title Splitting ──────────

class TestArtistTitleSplit:
    def test_dash_split(self):
        artist, title = AudioAnalyzer._split_artist_title("Andrés Calamaro - Crímenes perfectos")
        assert artist == "Andrés Calamaro"
        assert title == "Crímenes perfectos"

    def test_colon_split(self):
        artist, title = AudioAnalyzer._split_artist_title("Aterciopelados: Bolero falaz")
        assert artist == "Aterciopelados"
        assert title == "Bolero falaz"

    def test_em_dash_split(self):
        artist, title = AudioAnalyzer._split_artist_title("Ben E. King — Stand By Me")
        assert artist == "Ben E. King"
        assert title == "Stand By Me"

    def test_no_split_for_clean_title(self):
        artist, title = AudioAnalyzer._split_artist_title("Bohemian Rhapsody")
        assert artist is None
        assert title == "Bohemian Rhapsody"


# ─── Test 4: Core Words Extraction ───────────

class TestCoreWords:
    def test_removes_stopwords(self):
        result = AudioAnalyzer._extract_core_words("The Shape of You")
        assert "the" not in result.lower()
        assert "of" not in result.lower()
        assert "shape" in result.lower()

    def test_limits_to_three(self):
        result = AudioAnalyzer._extract_core_words("This Is A Very Long Title With Many Words")
        words = result.split()
        assert len(words) <= 3


# ─── Test 5: Live API — Known Track ──────────

class TestLiveAPI:
    def test_despacito(self, analyzer):
        time.sleep(2)
        result = analyzer.analyze_track(title="Despacito", artist="Luis Fonsi")
        assert result["bpm"] is not None
        assert 80 <= result["bpm"] <= 100
        assert result["key"] != "Unknown"
        assert result["danceability"] is not None

    def test_dash_title_format(self, analyzer):
        """Test a title with 'Artist - Song' format that previously failed."""
        time.sleep(2)
        result = analyzer.analyze_track(title="Black Sabbath - Iron Man", artist="Loukas Ch.")
        assert result["bpm"] is not None
        assert result["match_score"] >= 0.5


# ─── Test 6: Nonsense Rejection ──────────────

class TestRejection:
    def test_nonsense(self, analyzer):
        time.sleep(2)
        with pytest.raises((ValueError, Exception)):
            analyzer.analyze_track(title="xyzqwert8837nonsense", artist="")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
