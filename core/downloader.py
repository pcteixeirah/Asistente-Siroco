import os
import logging
import yt_dlp

logger = logging.getLogger(__name__)

class LowFiDownloader:
    def __init__(self, download_path, audio_format="bestaudio[abr<=64]/worst", proxy_pool=None, cookies_path=None):
        self.download_path = download_path
        self.audio_format = audio_format
        self.proxy_pool = proxy_pool
        self.cookies_path = cookies_path
        os.makedirs(self.download_path, exist_ok=True)
    
    def download_audio(self, yt_id):
        """
        Downloads low-fi audio for analysis.
        Returns absolute path to downloaded file.
        """
        url = f"https://www.youtube.com/watch?v={yt_id}"
        
        ydl_opts = {
            'format': self.audio_format,
            'outtmpl': os.path.join(self.download_path, '%(id)s.%(ext)s'),
            'postprocessors': [],  # No post-processing (keep original container for speed)
            'quiet': True,
            'no_warnings': True,
            'overwrites': True,
            'proxy': self.proxy_pool.get_proxy() if self.proxy_pool else None,
            'cookiefile': self.cookies_path if self.cookies_path and os.path.exists(self.cookies_path) else None,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                return os.path.abspath(filename)
        except Exception as e:
            logger.error(f"Download failed for {yt_id}: {e}")
            raise
