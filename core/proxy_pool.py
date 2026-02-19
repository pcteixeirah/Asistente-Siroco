import logging

logger = logging.getLogger(__name__)

class ProxyPool:
    """
    Manages proxy rotation strategies.
    Supported modes:
    - 'gateway': Uses a single gateway URL (e.g., BrightData, Smartproxy) that rotates IPs internally.
    - 'none': Direct connection (no proxy).
    """

    def __init__(self, config: dict):
        self.mode = config.get("mode", "none").lower()
        self.gateway_url = config.get("gateway_url")

        if self.mode == "gateway" and not self.gateway_url:
            logger.warning("Proxy mode is 'gateway' but no 'gateway_url' provided. Falling back to NO PROXY.")
            self.mode = "none"

        logger.info(f"ProxyPool initialized in mode: {self.mode}")

    def get_proxy(self) -> str | None:
        """
        Returns the current proxy URL to be used by yt-dlp.
        """
        if self.mode == "gateway":
            return self.gateway_url
        return None

    def rotate(self):
        """
        Triggers a proxy rotation. 
        For 'gateway' mode, this is mostly symbolic/logging, as the gateway rotates automatically 
        or per-request. But we log it to track retries.
        """
        if self.mode == "gateway":
            logger.info("Proxy rotation requested (Gateway handled). Retrying with fresh IP...")
        # Future: If mode == 'pool', implementation would switch to next proxy in list.
