# Phase 1: Foundation & Audio Analysis Tasks

## Setup Python Environment

- [x] Check Python availability
- [x] Create virtual environment (venv)
- [x] Install `ytmusicapi`
- [x] Create auth setup script `setup_auth.py`
- [x] Create `headers_auth.cfg`
- [x] Verify authentication
- [x] Create and run `get_account_info.py`
- [x] Create `tests` folder and move scripts
- [x] Clean up root directory
- [x] Create `README.md` with auth instructions
- [x] Create implementation plan for `get_playlist.py`
- [x] Create `tests/get_playlist.py`
- [x] Verify `get_playlist.py` with public playlist
- [x] Translate `README.md`
- [x] Initialize Git and commit "Get playlist"

## Audio Download Setup

- [x] Install `yt-dlp`
- [x] Create implementation plan for `download_tracks.py`
- [x] Install/Verify `ffmpeg`
- [x] Update `extract_playlist.py` (remove backup, add filepath)
- [x] Create `playlist` folder and `extract_playlist.py`
- [x] Implement full track extraction logic
- [x] Verify extraction with playlist `AZC`
- [x] Modify `extract_playlist.py` to use playlist title for filename
- [x] Create `playlist/download_tracks.py`
- [x] Modify `download_tracks.py` (clean filenames, retry logic, no JSON update)
- [x] Verify robust download (anti-bot measures)

## Playlist Enrichment

- [x] Investigate metadata sources
- [x] Create implementation plan for `enrich_playlist_data`
- [x] Implement enrichment logic (`popularity`, `demographic`, `energy`, `tags`, `playlist`) in `extract_playlist.py`
- [x] Modify `download_tracks.py` (remove spaces from filenames)
- [x] Verify new `siroco_playlist.json` structure

## Virtual DJ Integration

- [x] Verify Virtual DJ path and asset existence
- [x] Create `tests/test_vdj_connection.py` (launch VDJ with track)
- [x] Test VDJ launch and playback

## Audio Analysis (Librosa)

- [x] Install dependencies (`librosa`, `numpy`, `tqdm`, `pandas`)
- [x] Create `playlist/analyze_sample.py` with Key/BPM logic
- [x] Refactor `analyze_sample.py` to include Energy (RMS 1-10) analysis
- [x] Run analysis on `assets/` and generate CSV
