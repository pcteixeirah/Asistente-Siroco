# Proposed Folder Structure: Phase 2

This document outlines the target directory structure for the core system architecture (Phase 2).

```text
siroco-automation/
├── core/
│   ├── database.py       # SQLite management and CRUD operations
│   ├── analyzer.py       # Librosa analysis logic and audio downsampling
│   └── downloader.py     # yt-dlp wrapper with low-fidelity profiles
├── data/
│   ├── siroco_registry.db # SQLite Database file
│   └── temp_cache/       # Temporary folder (cleared after analysis)
├── logs/                 # YouTube API error logs
└── main_proxy.py         # Phase 2 Orchestrator script
```
