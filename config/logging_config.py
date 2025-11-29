import logging
import sys
from pathlib import Path
from config.settings import settings


def setup_logging():
    """Configure application logging"""
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "agent.log"),
        ]
    )
    
    logging.getLogger("livekit").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)