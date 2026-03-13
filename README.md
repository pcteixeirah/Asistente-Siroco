# Asistente Siroco: Project Architecture & Pipeline

This project acts as an automated pipeline for scanning, downloading, analyzing, and structuring YouTube Music libraries. This document outlines the core architecture and how data flows through the system.

### Acknowledgements
BPM and song key data used in this application is provided by the [GetSongBPM.com](https://getsongbpm.com) API.

## Project Structure & Architecture

The workspace is organized into a modular pipeline, separating configuration, core logic, data storage, and environment setup.

### 1. Root Files (The Entry Point & Configuration)
- **`main_proxy.py`**: The primary entry point and orchestrator for the application. It loads configurations, initializes the logging system, and weaves together the core modules (Database, Scanner, Downloader, Analyzer, and ProxyPool) to execute the end-to-end data pipeline.
- **`config.yaml`**: The centralized configuration file. It holds critical settings such as file paths, database constraints, download quality preferences, and logging configurations.

### 2. The `core/` Directory (Business Logic)
This folder holds the individual, decoupled modules that power the different stages of the pipeline:
- **`scanner.py`**: Interfaces with the `ytmusicapi` to scan YouTube Music playlists, retrieve track IDs, and extract metadata.
- **`downloader.py`**: Wraps `yt-dlp` to execute the actual downloading of audio tracks to temporary local storage.
- **`proxy_pool.py`**: Manages rotating proxy servers to mitigate rate limits and IP bans during high-volume scraping and downloading.
- **`analyzer.py`**: Uses `librosa` and `numpy` to perform acoustic analysis on downloaded audio files (e.g., bpm detection, key estimation) before the data is finalized.
- **`database.py`**: Handles all SQLite interactions. It manages the creation of tables, inserts new track metadata, and manages the registry of completed vs failed tracks.
- **`errors.py`**: Contains custom exception handling and specific error classification logic used to interpret why a proxy or download might have failed.
- **`config.py`**: A helper module tasked with parsing `config.yaml` and providing those constants safely to the rest of the application.

### 3. The `data/` Directory (Storage)
This folder is strictly for persistent and temporary data storage.
- **`siroco_registry.db`**: The master SQLite database. It serves as the single source of truth for all scanned and analyzed tracks.
- **`temp/` & `temp_cache/`**: Transient directories used by `downloader.py` and `analyzer.py` to store `.webm`/`.mp3` files momentarily during active acoustic analysis before they are discarded or moved.

### 4. The `setup/` Directory (Authentication)
Handles the connection bridging between the scripts and YouTube Music identity.
- **`headers_auth.cfg`**: The raw authentication file holding the session headers.
- **`create_auth_direct.py`**: A utility script used to regenerate `headers_auth.cfg` when session cookies expire.

---

## The Core Pipeline Workflow

The execution sequence generally follows these steps when `main_proxy.py` is invoked:

1. **Initialization**: `main_proxy.py` parses `config.yaml` via `core.config.py` and initializes the SQLite database connection (`siroco_registry.db`).
2. **Scanning**: `core.scanner.py` accesses YouTube Music (using credentials from `setup/`) to parse target playlists and extract video IDs and basic metadata.
3. **Downloading (with Proxies)**: The pipeline hands the track IDs to `core.downloader.py`. If proxying is enabled, `core.proxy_pool.py` routes the `yt-dlp` request through a designated proxy server to fetch the raw audio file into `data/temp/`.
4. **Analysis**: Once the audio is locally available, `core.analyzer.py` reads the file to calculate acoustic properties (like tempo and key).
5. **Registration**: The merged data (YouTube metadata + local acoustic analysis) is finalized and injected into the database via `core.database.py`. The temporary audio file is then purged to save space.
