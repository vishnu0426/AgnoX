import logging
from fastapi import APIRouter, Depends, HTTPException, status
import asyncpg
from pydantic import BaseModel

from app.api.dependencies import get_db_pool, verify_token
from app.api.schemas.queue_schema import (
    QueueStatusResponse,
    QueueStatsResponse,
    QueueEntryResponse
)
from app.services.queue_manager import QueueManager

logger = logging.getLogger(__name__)
router = APIRouter()


class PriorityUpdate(BaseModel):
    priority: int


@router.get("/queue/status", response_model=QueueStatusResponse)
async def get_queue_status(
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """Get current queue status"""
    try:
        queue_manager = QueueManager(db_pool)
        stats = await queue_manager.get_queue_stats()
        
        return QueueStatusResponse(**stats)
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve queue status"
        )


@router.get("/queue/stats", response_model=QueueStatsResponse)
async def get_queue_stats(
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """Get detailed queue statistics"""
    try:
        async with db_pool.acquire() as conn:
            entries = await conn.fetch(
                """
                SELECT queue_id, phone_number as customer_phone, room_name,
                       status, priority, queue_time, assigned_agent_id,
                       EXTRACT(EPOCH FROM (NOW() - queue_time)) as wait_seconds
                FROM call_queue
                WHERE status IN ('waiting', 'assigned')
                ORDER BY priority DESC, queue_time ASC
                """
            )
        
        queue_manager = QueueManager(db_pool)
        stats = await queue_manager.get_queue_stats()
        
        return QueueStatsResponse(
            entries=[QueueEntryResponse(**dict(entry)) for entry in entries],
            stats=QueueStatusResponse(**stats)
        )
    except Exception as e:
        logger.error(f"Failed to get queue stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve queue statistics"
        )


@router.post("/queue/{queue_id}/priority", response_model=dict)
async def update_queue_priority(
    queue_id: int,
    priority_update: PriorityUpdate,
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """Update queue entry priority"""
    try:
        async with db_pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE call_queue
                SET priority = $1
                WHERE queue_id = $2
                """,
                priority_update.priority,
                queue_id
            )
            
            if result == "UPDATE 0":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Queue entry not found"
                )
            
            return {
                "success": True,
                "queue_id": queue_id,
                "new_priority": priority_update.priority
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update queue priority: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update queue priority"
        )