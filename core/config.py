"""
SIROCO Config Loader
Reads config.yaml from the project root and provides defaults.
"""

import os
import yaml
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Project root = parent of core/
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_PATH = os.path.join(_PROJECT_ROOT, "config.yaml")

# Defaults (used if a key is missing from the YAML)
_DEFAULTS = {
    "paths": {
        "database": "data/siroco_registry.db",
        "log_file": "logs/process.log",
        "auth_config": "setup/headers_auth.cfg",
    },
    "playlist": {
        "default_id": "PLXlz4-GmC7VsuHrQgBg40CHHqFftdVNqJ",
    },
    "batch": {
        "size": 50,
        "delay_seconds": 2,
        "max_retries": 3,
        "max_tracks_to_process": 500,
    },
    "spotify": {
        "timeout_seconds": 15,
        "max_retries": 5,
    },
}


def _deep_merge(defaults: dict, overrides: dict) -> dict:
    """Recursively merge overrides into defaults."""
    result = defaults.copy()
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_path: str = None) -> dict:
    """
    Load configuration from config.yaml, merged with defaults.
    All relative paths are resolved against the project root.
    """
    path = config_path or _CONFIG_PATH

    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}
            config = _deep_merge(_DEFAULTS, user_config)
            logger.info(f"Configuration loaded from {path}")
        except Exception as e:
            logger.warning(f"Error reading {path}: {e}. Using defaults.")
            config = _DEFAULTS.copy()
    else:
        logger.warning(f"Config file not found at {path}. Using defaults.")
        config = _DEFAULTS.copy()

    # Resolve relative paths against project root
    for key, value in config["paths"].items():
        if not os.path.isabs(value):
            config["paths"][key] = os.path.join(_PROJECT_ROOT, value)

    return config
