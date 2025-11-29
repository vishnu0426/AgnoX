import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
import asyncpg

from app.api.dependencies import get_db_pool, verify_token
from app.api.schemas.analytics_schema import (
    RealtimeMetricsResponse,
    CallMetricsResponse,
    AgentPerformanceResponse
)
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/analytics/realtime", response_model=RealtimeMetricsResponse)
async def get_realtime_metrics(
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """Get real-time call center metrics"""
    try:
        analytics_service = AnalyticsService(db_pool)
        metrics = await analytics_service.get_realtime_metrics()
        
        return RealtimeMetricsResponse(**metrics)
    except Exception as e:
        logger.error(f"Failed to get realtime metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve realtime metrics"
        )


@router.get("/analytics/calls", response_model=CallMetricsResponse)
async def get_call_metrics(
    start_date: datetime = Query(default=None),
    end_date: datetime = Query(default=None),
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """Get call analytics for date range"""
    try:
        if not start_date:
            start_date = datetime.now() - timedelta(days=7)
        if not end_date:
            end_date = datetime.now()
        
        analytics_service = AnalyticsService(db_pool)
        metrics = await analytics_service.get_call_metrics(start_date, end_date)
        
        return CallMetricsResponse(**metrics)
    except Exception as e:
        logger.error(f"Failed to get call metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve call metrics"
        )


@router.get("/analytics/agents/{agent_id}", response_model=AgentPerformanceResponse)
async def get_agent_performance(
    agent_id: int,
    days: int = Query(default=30, ge=1, le=90),
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """Get agent performance metrics"""
    try:
        analytics_service = AnalyticsService(db_pool)
        performance = await analytics_service.get_agent_performance(agent_id, days)
        
        if not performance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found or no data available"
            )
        
        return AgentPerformanceResponse(**performance)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent performance"
        )