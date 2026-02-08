# Phase 1: Implementation Walkthrough

## Environment Setup

- **Python**: 3.12.6
- **Virtual Env**: `venv/` created.
- **Libraries**: `ytmusicapi` (API), `yt-dlp` (Download), `librosa` (Analysis), `pandas`, `numpy`, `tqdm`.

## Authentication

- **setup/headers_auth.cfg**: Configured from raw headers.
- **scripts**: `setup/create_auth_direct.py` parser.

## Core Features

### 1. Playlist Extraction (`playlist/extract_playlist.py`)

- Fetches all tracks from a YouTube Music playlist (e.g., "AZC").
- **Enrichment**: Adds simulated metadata for DJ analysis:
  - `popularity` (0-100)
  - `energy` (1-10, mock)
  - `demographic` (Family/Couple/Social)
  - `playlist` (Source name)
- **Output**: `playlist/siroco_playlist.json`.

### 2. Audio Downloading (`playlist/download_tracks.py`)

- Downloads random samples to `assets/`.
- **Robustness**:
  - Handles YouTube 403 Forbidden errors with retry loop and delays.
  - Uses specific User-Agent.
- **Naming**: `Artist_-_Title.mp3` (Space-free).

### 3. Audio Analysis (`playlist/analyze_sample.py`)

- Uses `librosa` to analyze tracks in `assets/`.
- **Metrics**:
  - **BPM**: Tempo detection.
  - **Key**: Tonal distance correlation (Krumhansl-Schmuckler) to estimate Key (e.g., "G maj").
  - **Energy**: RMS amplitude scaled to 1-10.
- **Output**: `assets/audio_analysis.csv`.

### 4. Virtual DJ Integration (`tests/test_vdj_connection.py`)

- Launches `virtualdj.exe` via `subprocess`.
- Loads a specific track passed as CLI argument.

## Project Structure

- **assets/**: Downloaded MP3s and `audio_analysis.csv`.
- **playlist/**: Core scripts (`extract`, `download`, `analyze`) and JSON data.
- **setup/**: Auth tools.
- **tests/**: VDJ connection test, metadata checks.
- **docs/**: Consolidated documentation.
