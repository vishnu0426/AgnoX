import asyncio
import asyncpg
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from app.services.queue_manager import QueueManager

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main queue processor"""
    
    database_url = settings.database_url
    if not database_url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)
    
    logger.info("Starting Queue Processor...")
    
    try:
        # Create database pool
        db_pool = await asyncpg.create_pool(
            dsn=database_url,
            min_size=2,
            max_size=10
        )
        logger.info("Database connection pool created")
        
        # Create queue manager
        queue_manager = QueueManager(db_pool)
        
        # Start processing
        logger.info("Queue processor started")
        await queue_manager.start_queue_processor()
        
    except KeyboardInterrupt:
        logger.info("Shutting down queue processor...")
    except Exception as e:
        logger.error(f"Queue processor error: {e}")
        sys.exit(1)
    finally:
        if db_pool:
            await db_pool.close()
        logger.info("Queue processor stopped")


if __name__ == "__main__":
    asyncio.run(main())