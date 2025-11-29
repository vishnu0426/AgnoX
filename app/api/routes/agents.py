import logging
from fastapi import APIRouter, Depends, HTTPException, status
import asyncpg

from app.api.dependencies import get_db_pool, verify_token
from app.api.schemas.agent_schema import (
    AgentResponse,
    AgentListResponse,
    AgentStatusUpdate
)
from app.services.queue_manager import QueueManager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/agents", response_model=AgentListResponse)
async def list_agents(
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """List all agents"""
    try:
        async with db_pool.acquire() as conn:
            agents = await conn.fetch(
                """
                SELECT agent_id, name, phone_number, status,
                       current_call_count, max_concurrent_calls, skills
                FROM agents
                ORDER BY name
                """
            )
            
            return AgentListResponse(
                agents=[AgentResponse(**dict(agent)) for agent in agents],
                total=len(agents)
            )
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agents"
        )


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: int,
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """Get agent details"""
    try:
        async with db_pool.acquire() as conn:
            agent = await conn.fetchrow(
                """
                SELECT agent_id, name, phone_number, status,
                       current_call_count, max_concurrent_calls, skills
                FROM agents
                WHERE agent_id = $1
                """,
                agent_id
            )
            
            if not agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found"
                )
            
            return AgentResponse(**dict(agent))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent"
        )


@router.put("/agents/{agent_id}/status", response_model=dict)
async def update_agent_status(
    agent_id: int,
    status_update: AgentStatusUpdate,
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """Update agent status"""
    try:
        queue_manager = QueueManager(db_pool)
        
        from app.utils.constants import AgentStatus
        status_enum = AgentStatus(status_update.status)
        
        success = await queue_manager.update_agent_status(
            agent_id,
            status_enum
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        return {
            "success": True,
            "agent_id": agent_id,
            "status": status_update.status
        }
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status value"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update agent status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update agent status"
        )
