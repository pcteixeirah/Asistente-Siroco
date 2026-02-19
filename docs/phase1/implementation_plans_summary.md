# Phase 1: Implementation Plans Summary

## 1. Playlist Data Enrichment

**Goal**: Expand `siroco_playlist.json` for DJ Agent analysis.
**Strategy**: Since API lacks subjective data ("Vibe"), we use **Mock Data** to unblock development.

- **Fields Added**:
  - `popularity`: 0-100 (Random mock)
  - `demographic`: Enum [Family, Couple, Social] (Random mock)
  - `energy`: 1-10 (Random mock)
  - `tags`: List (Empty)
- **Outcome**: Implemented in `extract_playlist.py`.

## 2. Audio Analysis (Librosa)

**Goal**: Extract objective technical metrics from audio files.
**Strategy**: Use `librosa` on `assets/` folder.

- **Metrics**:
  - **BPM**: Standard beat tracking.
  - **Key**: Chromagram correlation with Major/Minor chord profiles.
  - **Energy**: Root Mean Square (RMS) energy, scaled x100 and clamped to 1-10 range.
- **Outcome**: Implemented in `analyze_sample.py`, generating `audio_analysis.csv`.

## 3. Robust Audio Download

**Goal**: Reliable downloading despite YouTube bot detection (403 errors).
**Strategy**:

- **Loop**: Retry until Target Count (5) is met.
- **Evasion**: Random sleep intervals (5-10s pre, 10-15s post-error), User-Agent spoofing.
- **Naming**: Sanitize filenames to `Artist_{sep}_Title.mp3`.
- **Outcome**: Implemented in `download_tracks.py`.
