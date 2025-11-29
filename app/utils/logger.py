import logging
from typing import Optional


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get configured logger instance
    
    Args:
        name: Logger name (usually __name__)
        level: Optional log level override
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    
    if level:
        logger.setLevel(getattr(logging, level.upper()))
    return logger