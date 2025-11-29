from livekit import api
from config.settings import settings


class LiveKitConfig:
    """LiveKit API configuration"""
    
    @staticmethod
    def get_api_client() -> api.LiveKitAPI:
        """Get LiveKit API client"""
        return api.LiveKitAPI(
            url=settings.livekit_url,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret
        )


livekit_config = LiveKitConfig()