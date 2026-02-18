import os
import logging
import yt_dlp

logger = logging.getLogger(__name__)

class LowFiDownloader:
    def __init__(self, download_path="data/temp_cache"):
        self.download_path = download_path
        os.makedirs(self.download_path, exist_ok=True)
    
    def download_audio(self, yt_id):
        """
        Downloads low-fi audio for analysis.
        Returns absolute path to downloaded file.
        """
        url = f"https://www.youtube.com/watch?v={yt_id}"
        
        ydl_opts = {
            'format': 'bestaudio[abr<=64]/worst', # Low bitrate preference
            'outtmpl': os.path.join(self.download_path, '%(id)s.%(ext)s'),
            'postprocessors': [], # No post-processing (keep original container for speed)
            'quiet': True,
            'no_warnings': True,
            'overwrites': True,
            # 'logger': logger # Can bind logger if needed, but might be noisy
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                return os.path.abspath(filename)
        except Exception as e:
            logger.error(f"Download failed for {yt_id}: {e}")
            raise
