import asyncpg
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Analytics and reporting service"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def get_realtime_metrics(self) -> Dict:
        """Get real-time call center metrics"""
        async with self.db_pool.acquire() as conn:
            try:
                stats = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE status = 'waiting') as calls_waiting,
                        COUNT(*) FILTER (WHERE status = 'assigned') as calls_active,
                        AVG(EXTRACT(EPOCH FROM (NOW() - queue_time)))
                            FILTER (WHERE status = 'waiting') as avg_wait_time,
                        (SELECT COUNT(*) FROM agents WHERE status = 'online') as agents_available,
                        (SELECT COUNT(*) FROM agents WHERE status = 'busy') as agents_busy
                    FROM call_queue
                    WHERE status IN ('waiting', 'assigned')
                    """
                )
                
                return {
                    "calls_waiting": stats['calls_waiting'] or 0,
                    "calls_active": stats['calls_active'] or 0,
                    "avg_wait_time": float(stats['avg_wait_time'] or 0),
                    "agents_available": stats['agents_available'] or 0,
                    "agents_busy": stats['agents_busy'] or 0,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Error getting realtime metrics: {e}")
                return {}
    
    async def get_call_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Get call analytics for date range"""
        if not start_date:
            start_date = datetime.now() - timedelta(days=7)
        if not end_date:
            end_date = datetime.now()
        
        async with self.db_pool.acquire() as conn:
            try:
                metrics = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) as total_calls,
                        AVG(duration_seconds) as avg_call_duration,
                        COUNT(*) FILTER (WHERE handled_by = 'ai') as ai_handled,
                        COUNT(*) FILTER (WHERE handled_by = 'human') as human_handled,
                        COUNT(*) FILTER (WHERE transfer_count > 0) as transfers
                    FROM call_sessions
                    WHERE start_time BETWEEN $1 AND $2
                    """,
                    start_date,
                    end_date
                )
                
                return dict(metrics)
            except Exception as e:
                logger.error(f"Error getting call metrics: {e}")
                return {}
    
    async def get_agent_performance(
        self,
        agent_id: int,
        days: int = 30
    ) -> Dict:
        """Get agent performance metrics"""
        async with self.db_pool.acquire() as conn:
            try:
                start_date = datetime.now() - timedelta(days=days)
                
                performance = await conn.fetchrow(
                    """
                    SELECT
                        a.name,
                        COUNT(cs.session_id) as total_calls,
                        AVG(cs.duration_seconds) as avg_call_duration,
                        SUM(cs.duration_seconds) as total_talk_time
                    FROM agents a
                    LEFT JOIN call_sessions cs ON a.agent_id = cs.agent_id
                    WHERE a.agent_id = $1
                    AND cs.start_time >= $2
                    GROUP BY a.agent_id, a.name
                    """,
                    agent_id,
                    start_date
                )
                
                return dict(performance) if performance else {}
            except Exception as e:
                logger.error(f"Error getting agent performance: {e}")
                return {}
