import pytest
import asyncpg
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_pool():
    """Create test database pool"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL not set")
    
    pool = await asyncpg.create_pool(
        dsn=database_url,
        min_size=1,
        max_size=5
    )
    yield pool
    await pool.close()


@pytest.fixture
async def db_connection(db_pool):
    """Create test database connection"""
    conn = await db_pool.acquire()
    yield conn
    await db_pool.release(conn)


@pytest.fixture
def sample_customer_data():
    """Sample customer data for tests"""
    return {
        "phone_number": "+1234567890",
        "name": "Test Customer",
        "email": "test@example.com"
    }


@pytest.fixture
def sample_agent_data():
    """Sample agent data for tests"""
    return {
        "name": "Test Agent",
        "phone_number": "+1987654321",
        "status": "online",
        "max_concurrent_calls": 2,
        "skills": {"departments": ["general", "billing"]}
    }


@pytest.mark.asyncio
async def test_database_connection(db_pool):
    """Test database connection"""
    async with db_pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
        assert result == 1