import asyncio
import asyncpg
from typing import Optional
from config.settings import settings


class DatabaseManager:
    """Database connection manager, safe across multiple event loops."""

    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def connect(self):
        """
        Create database connection pool.

        NOTE: LiveKit workers may create new event loops for different jobs.
        If a pool exists but was created in a different loop, we close it and
        create a new one bound to the current loop to avoid
        'Future attached to a different loop' errors.
        """
        loop = asyncio.get_running_loop()

        # If we already have a pool but it's bound to a different loop,
        # close it and reset.
        if self._pool is not None and self._loop is not loop:
            try:
                await self._pool.close()
            except Exception:
                # Best-effort close; don't crash on shutdown errors
                pass
            self._pool = None
            self._loop = None

        # Create a new pool if needed
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=settings.database_url,
                min_size=settings.database_pool_min_size,
                max_size=settings.database_pool_max_size,
                command_timeout=60,
            )
            self._loop = loop

    async def disconnect(self):
        """Close database connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._loop = None

    @property
    def pool(self) -> asyncpg.Pool:
        """Get connection pool."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        return self._pool


db_manager = DatabaseManager()
