import os
import logging
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import time

logger = logging.getLogger(__name__)

# Standard pitch class to Key Name mapping (0 = C, 1 = C#, 2 = D, etc.)
PITCH_CLASS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
MODE_CLASS = ['min', 'maj']

class AudioAnalyzer:
    """
    Analyzes audio features using the Spotify Web API.
    Replaces the local librosa processing.
    """
    def __init__(self, config=None):
        """
        Initializes the Spotipy client using credentials from environment variables.
        Requires SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET.
        """
        if config is None:
            config = {}
            
        self.timeout = config.get("timeout_seconds", 15)
        self.max_retries = config.get("max_retries", 5)

        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

        if not client_id or not client_secret or client_id == "tu_client_id_aqui":
            logger.error("Spotify credentials not found or not configured in .env")
            raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set.")

        # spotipy auth_manager handles token fetching and refreshing automatically
        auth_manager = SpotifyClientCredentials(
            client_id=client_id, 
            client_secret=client_secret
        )
        self.sp = spotipy.Spotify(
            auth_manager=auth_manager,
            requests_timeout=self.timeout,
            retries=self.max_retries,
            status_forcelist=(429, 500, 502, 503, 504) # Retry on rate limits and server errors
        )
        logger.info("Spotify API Client Initialized.")

    def search_track(self, query: str) -> str:
        """
        Searches for a track on Spotify and returns its Spotify ID.
        """
        try:
            results = self.sp.search(q=query, type='track', limit=1)
            tracks = results.get('tracks', {}).get('items', [])
            
            if not tracks:
                logger.warning(f"No match found on Spotify for query: '{query}'")
                return None
                
            track = tracks[0]
            spotify_id = track.get('id')
            spotify_name = track.get('name')
            
            # Extract artists for logging
            artists = ", ".join([a.get('name') for a in track.get('artists', [])])
            logger.debug(f"Search '{query}' -> Found: '{spotify_name}' by {artists} (ID: {spotify_id})")
            
            return spotify_id
            
        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Spotify API Search Error for '{query}': {e}")
            raise
        except Exception as e:
            logger.error(f"Unknown error during track search '{query}': {e}")
            raise

    def get_audio_features(self, spotify_id: str) -> dict:
        """
        Fetches audio features for a specific Spotify ID.
        Formats the results to match SIROCO's database schema.
        """
        try:
            features_list = self.sp.audio_features([spotify_id])
            
            if not features_list or not features_list[0]:
                logger.warning(f"No audio features available for Spotify ID: {spotify_id}")
                return None
                
            f = features_list[0]
            
            # Format Key (0-11) and Mode (0=minor, 1=major) -> e.g., 'C maj', 'A min'
            key_val = f.get('key', -1)
            mode_val = f.get('mode', -1)
            formatted_key = "Unknown"
            if 0 <= key_val <= 11 and mode_val in [0, 1]:
                formatted_key = f"{PITCH_CLASS[key_val]} {MODE_CLASS[mode_val]}"

            # Convert duration_ms to seconds
            duration_s = round(f.get('duration_ms', 0) / 1000.0, 2)

            results = {
                "bpm": int(round(f.get('tempo', 0))), # Keep BPM as int for DB schema compatibility
                "key": formatted_key,
                "energy_rms": f.get('energy', 0.0), # Spotify returns 0.0 to 1.0 float
                "duration": duration_s,
                "danceability": f.get('danceability', 0.0),
                "valence": f.get('valence', 0.0),
                "spotify_id": spotify_id
            }
            return results
            
        except Exception as e:
            logger.error(f"Failed to fetch features for ID {spotify_id}: {e}")
            raise

    def analyze_track(self, title: str, artist: str = "") -> dict:
        """
        High-level method that combines search and feature extraction.
        Takes a track title (and optionally artist) from YT, finds it on Spotify,
        and returns the audio features.
        """
        # Clean query: e.g. remove "(Official Video)", "[Audio]" etc.
        query = title
        if artist:
            query = f"{title} artist:{artist}"
            
        logger.info(f"  -> Searching Spotify for: '{query}'")
        spotify_id = self.search_track(query)
        
        if not spotify_id:
            raise ValueError(f"Track not found on Spotify")
            
        logger.info(f"  -> Fetching Audio Features...")
        features = self.get_audio_features(spotify_id)
        
        if not features:
            raise ValueError(f"Features not available for track")
            
        return features
