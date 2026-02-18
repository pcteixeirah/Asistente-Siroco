import librosa
import numpy as np
import os
import logging

logger = logging.getLogger(__name__)

# Constants
SAMPLE_RATE = 22050
MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

class AudioAnalyzer:
    def _estimate_key(self, y, sr):
        """
        Estimates Key using Krumhansl-Schmuckler algorithm (simplified).
        """
        try:
            chroma = librosa.feature.chroma_cens(y=y, sr=sr)
            chroma_mean = np.mean(chroma, axis=1)
            
            maj_corrs = []
            min_corrs = []
            
            for i in range(12):
                profile_maj = np.roll(MAJOR_PROFILE, i)
                profile_min = np.roll(MINOR_PROFILE, i)
                maj_corrs.append(np.corrcoef(chroma_mean, profile_maj)[0, 1])
                min_corrs.append(np.corrcoef(chroma_mean, profile_min)[0, 1])
                
            best_maj_idx = np.argmax(maj_corrs)
            best_min_idx = np.argmax(min_corrs)
            
            if maj_corrs[best_maj_idx] > min_corrs[best_min_idx]:
                return f"{NOTE_NAMES[best_maj_idx]} maj"
            else:
                return f"{NOTE_NAMES[best_min_idx]} min"
        except Exception as e:
            logger.warning(f"Key estimation failed: {e}")
            return None

    def analyze_track(self, filepath):
        """
        Analyzes audio file for BPM, Key, Energy, Duration.
        Deletes the file after analysis.
        """
        try:
            # Load with low SR and Mono
            y, sr = librosa.load(filepath, sr=SAMPLE_RATE, mono=True)
            
            # BPM
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            bpm = int(round(tempo)) if isinstance(tempo, float) else int(round(tempo[0]))
            
            # Key
            key = self._estimate_key(y, sr)
            
            # Energy (RMS)
            rms = librosa.feature.rms(y=y)
            rms_mean = np.mean(rms)
            energy_score = int(min(max(rms_mean * 100, 1), 10))
            
            # Duration
            duration = librosa.get_duration(y=y, sr=sr)
            
            results = {
                "bpm": bpm,
                "key": key,
                "energy_rms": energy_score,
                "duration": round(duration, 2)
            }
            
            return results

        except Exception as e:
            logger.error(f"Analysis failed for {filepath}: {e}")
            raise
        finally:
            # Cleanup
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    logger.info(f"Deleted temp file: {filepath}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to delete temp file {filepath}: {cleanup_error}")
