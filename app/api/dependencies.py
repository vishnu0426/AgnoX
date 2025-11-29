from typing import Optional, AsyncGenerator
import asyncpg
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config.database import db_manager
from config.settings import settings

security = HTTPBearer()


async def get_db_pool() -> asyncpg.Pool:
    """Dependency to get database connection pool"""
    if db_manager.pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available"
        )
    return db_manager.pool


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Verify JWT token (implement your auth logic)"""
    token = credentials.credentials
    # TODO: Implement actual JWT verification
    # For now, check if token matches API secret key
    if settings.debug or token == settings.api_secret_key:
        return token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials"
    )