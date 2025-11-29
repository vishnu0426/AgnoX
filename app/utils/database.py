import asyncpg
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


async def execute_query(
    pool: asyncpg.Pool,
    query: str,
    *args,
    fetch_one: bool = False,
    fetch_all: bool = False
) -> Optional[Any]:
    """
    Execute database query with error handling
    
    Args:
        pool: Database connection pool
        query: SQL query
        *args: Query parameters
        fetch_one: Return single row
        fetch_all: Return all rows
        
    Returns:
        Query result or None
    """
    async with pool.acquire() as conn:
        try:
            if fetch_one:
                return await conn.fetchrow(query, *args)
            elif fetch_all:
                return await conn.fetch(query, *args)
            else:
                return await conn.execute(query, *args)
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            logger.error(f"Query: {query}")
            raise({e})