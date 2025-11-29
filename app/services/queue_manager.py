"""
Queue Manager for Customer Service Voice Agent
Handles call queuing, agent assignment, and queue processing
"""

import asyncio
import asyncpg
import logging
from typing import Optional, Dict, List
from enum import Enum
from datetime import datetime
import json

from livekit import api  # LiveKit Agent Dispatch API

logger = logging.getLogger(__name__)


class QueuePriority(Enum):
    """Queue priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class QueueStatus(Enum):
    """Queue entry status"""
    WAITING = "waiting"
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class AgentStatus(Enum):
    """Agent availability status"""
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"
    AWAY = "away"


class QueueManager:
    """Manages call queue and agent assignment"""

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize queue manager

        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool
        self.check_interval = 2  # seconds
        logger.info("QueueManager initialized")

    async def add_to_queue(
        self,
        customer_id: int,
        phone_number: str,
        room_name: str,
        priority: int = QueuePriority.NORMAL.value,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Add a caller to the queue

        Args:
            customer_id: Customer database ID
            phone_number: Customer phone number
            room_name: LiveKit room name
            priority: Queue priority (0-3)
            metadata: Additional metadata as dict

        Returns:
            queue_id: ID of queue entry

        Raises:
            Exception: If database operation fails
        """
        async with self.db_pool.acquire() as conn:
            try:
                # Convert metadata dict to JSON string for PostgreSQL
                metadata_json = json.dumps(metadata or {})

                queue_entry = await conn.fetchrow(
                    """
                    INSERT INTO call_queue
                    (customer_id, phone_number, room_name, priority, status, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                    RETURNING queue_id
                    """,
                    customer_id,
                    phone_number,
                    room_name,
                    priority,
                    QueueStatus.WAITING.value,
                    metadata_json
                )

                queue_id = queue_entry["queue_id"]
                logger.info(
                    f"Added to queue: {queue_id} for customer {customer_id} "
                    f"from {phone_number} with priority {priority}"
                )
                return queue_id

            except asyncpg.exceptions.UniqueViolationError as e:
                logger.error(f"Duplicate entry in queue: {e}", exc_info=True)
                raise
            except asyncpg.exceptions.ForeignKeyViolationError as e:
                logger.error(f"Foreign key violation: {e}", exc_info=True)
                raise
            except Exception as e:
                logger.error(f"Error adding to queue: {e}", exc_info=True)
                raise

    async def get_available_agent(self) -> Optional[int]:
        """
        Find an available agent

        Returns:
            agent_id or None if no agent available
        """
        async with self.db_pool.acquire() as conn:
            try:
                agent = await conn.fetchrow(
                    """
                    SELECT agent_id
                    FROM agents
                    WHERE status = 'online'
                    AND current_call_count < max_concurrent_calls
                    ORDER BY current_call_count ASC
                    LIMIT 1
                    """
                )

                if agent:
                    agent_id = agent["agent_id"]
                    logger.debug(f"Found available agent: {agent_id}")
                    return agent_id
                else:
                    logger.debug("No available agents")
                    return None

            except Exception as e:
                logger.error(f"Error finding available agent: {e}", exc_info=True)
                return None

    async def assign_to_agent(self, queue_id: int, agent_id: int) -> bool:
        """
        Assign a queued call to an agent

        Args:
            queue_id: Queue entry ID
            agent_id: Agent ID

        Returns:
            True if successful, False otherwise
        """
        async with self.db_pool.acquire() as conn:
            try:
                async with conn.transaction():
                    # Update queue entry
                    await conn.execute(
                        """
                        UPDATE call_queue
                        SET status = $1, assigned_agent_id = $2, assigned_at = $3
                        WHERE queue_id = $4
                        """,
                        QueueStatus.ASSIGNED.value,
                        agent_id,
                        datetime.now(),
                        queue_id,
                    )

                    # Increment agent call count
                    await conn.execute(
                        """
                        UPDATE agents
                        SET current_call_count = current_call_count + 1
                        WHERE agent_id = $1
                        """,
                        agent_id,
                    )

                    logger.info(f"Assigned queue entry {queue_id} to agent {agent_id}")
                    return True

            except Exception as e:
                logger.error(f"Error assigning to agent: {e}", exc_info=True)
                return False

    async def mark_completed(self, queue_id: int) -> bool:
        """
        Mark queue entry as completed

        Args:
            queue_id: Queue entry ID

        Returns:
            True if successful
        """
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    UPDATE call_queue
                    SET status = $1, completed_at = $2
                    WHERE queue_id = $3
                    """,
                    QueueStatus.COMPLETED.value,
                    datetime.now(),
                    queue_id,
                )

                logger.info(f"Marked queue entry {queue_id} as completed")
                return True

            except Exception as e:
                logger.error(f"Error marking completed: {e}", exc_info=True)
                return False

    async def mark_abandoned(self, queue_id: int) -> bool:
        """
        Mark queue entry as abandoned

        Args:
            queue_id: Queue entry ID

        Returns:
            True if successful
        """
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    UPDATE call_queue
                    SET status = $1, abandoned_at = $2
                    WHERE queue_id = $3
                    """,
                    QueueStatus.ABANDONED.value,
                    datetime.now(),
                    queue_id,
                )

                logger.info(f"Marked queue entry {queue_id} as abandoned")
                return True

            except Exception as e:
                logger.error(f"Error marking abandoned: {e}", exc_info=True)
                return False

    async def get_queue_position(self, queue_id: int) -> Optional[int]:
        """
        Get position in queue

        Args:
            queue_id: Queue entry ID

        Returns:
            Position in queue (1-indexed) or None
        """
        async with self.db_pool.acquire() as conn:
            try:
                result = await conn.fetchrow(
                    """
                    SELECT COUNT(*) as position
                    FROM call_queue
                    WHERE status = $1
                    AND (
                        priority > (SELECT priority FROM call_queue WHERE queue_id = $2)
                        OR (
                            priority = (SELECT priority FROM call_queue WHERE queue_id = $2)
                            AND queue_id <= $2
                        )
                    )
                    """,
                    QueueStatus.WAITING.value,
                    queue_id,
                )

                if result:
                    return result["position"]
                return None

            except Exception as e:
                logger.error(f"Error getting queue position: {e}", exc_info=True)
                return None

    async def get_queue_stats(self) -> Dict:
        """
        Get queue statistics

        Returns:
            Dictionary with queue stats
        """
        async with self.db_pool.acquire() as conn:
            try:
                stats = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE status = 'waiting') as waiting_count,
                        COUNT(*) FILTER (WHERE status = 'assigned') as assigned_count,
                        AVG(EXTRACT(EPOCH FROM (assigned_at - join_time)))
                            FILTER (WHERE assigned_at IS NOT NULL) as avg_wait_time_seconds
                    FROM call_queue
                    WHERE join_time > NOW() - INTERVAL '1 hour'
                    """
                )

                agent_stats = await conn.fetchrow(
                    """
                    SELECT COUNT(*) as active_agents
                    FROM agents
                    WHERE status = 'online'
                    """
                )

                return {
                    "waiting_count": stats["waiting_count"] or 0,
                    "assigned_count": stats["assigned_count"] or 0,
                    "avg_wait_time_seconds": float(
                        stats["avg_wait_time_seconds"] or 0
                    ),
                    "active_agents": agent_stats["active_agents"] or 0,
                }

            except Exception as e:
                logger.error(f"Error getting queue stats: {e}", exc_info=True)
                return {
                    "waiting_count": 0,
                    "assigned_count": 0,
                    "avg_wait_time_seconds": 0.0,
                    "active_agents": 0,
                }

    async def get_waiting_calls(self) -> List[Dict]:
        """
        Get all waiting calls in queue

        Returns:
            List of waiting queue entries
        """
        async with self.db_pool.acquire() as conn:
            try:
                rows = await conn.fetch(
                    """
                    SELECT queue_id, customer_id, phone_number, room_name,
                           priority, join_time, metadata
                    FROM call_queue
                    WHERE status = $1
                    ORDER BY priority DESC, join_time ASC
                    """,
                    QueueStatus.WAITING.value,
                )

                return [dict(row) for row in rows]

            except Exception as e:
                logger.error(f"Error getting waiting calls: {e}", exc_info=True)
                return []

    async def dispatch_to_ai(self, call: Dict) -> bool:
        """
        Dispatch a waiting call to the LiveKit AI agent via explicit agent dispatch.

        Uses environment variables LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
        for authentication (as recommended by LiveKit). 
        """
        queue_id = call["queue_id"]
        room_name = call["room_name"]

        logger.info(
            f"No human agent available -> dispatching queue entry {queue_id} "
            f"in room {room_name} to AI agent"
        )

        try:
            # Initialize LiveKit API client (reads env vars by default)
            lkapi = api.LiveKitAPI()

            metadata_payload = {
                "queue_id": queue_id,
                "customer_id": call.get("customer_id"),
                "phone_number": call.get("phone_number"),
                "priority": call.get("priority"),
            }

            dispatch = await lkapi.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name="AgnoX-AI-Agent",  # must match gemini_agent.py
                    room=room_name,
                    metadata=json.dumps(metadata_payload),
                )
            )

            logger.info(
                "Created AI agent dispatch %s for queue entry %s",
                getattr(dispatch, "dispatch_id", getattr(dispatch, "id", "unknown")),
                queue_id,
            )

            # Mark queue entry as assigned (AI, no human agent_id)
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE call_queue
                    SET status = $1, assigned_at = $2
                    WHERE queue_id = $3
                    """,
                    QueueStatus.ASSIGNED.value,
                    datetime.now(),
                    queue_id,
                )

            await lkapi.aclose()
            return True

        except Exception as e:
            logger.error(
                f"Error dispatching queue entry {queue_id} to AI agent: {e}",
                exc_info=True,
            )
            return False

    async def process_queue(self):
        """
        Process queue - assign waiting calls to available agents.
        If no human agent is available, fall back to AI voice agent.
        """
        try:
            waiting_calls = await self.get_waiting_calls()

            if not waiting_calls:
                logger.debug("No calls waiting in queue")
                return

            logger.info(f"Processing {len(waiting_calls)} waiting call(s)")

            for call in waiting_calls:
                agent_id = await self.get_available_agent()

                # Prefer human agents if available
                if agent_id:
                    success = await self.assign_to_agent(
                        call["queue_id"],
                        agent_id,
                    )

                    if success:
                        logger.info(
                            f"Assigned call from {call['phone_number']} "
                            f"to human agent {agent_id}"
                        )
                    continue

                # No human agent -> dispatch to AI
                ai_success = await self.dispatch_to_ai(call)
                if ai_success:
                    logger.info(
                        f"Assigned call from {call['phone_number']} "
                        f"to AI voice agent (queue_id={call['queue_id']})"
                    )
                else:
                    logger.error(
                        f"Failed to dispatch queue entry {call['queue_id']} to AI agent"
                    )

        except Exception as e:
            logger.error(f"Error processing queue: {e}", exc_info=True)

    async def start_queue_processor(self):
        """
        Start continuous queue processing loop
        """
        logger.info("Starting queue processor loop")

        try:
            while True:
                await self.process_queue()
                await asyncio.sleep(self.check_interval)

        except asyncio.CancelledError:
            logger.info("Queue processor stopped")
        except Exception as e:
            logger.error(f"Queue processor error: {e}", exc_info=True)
            raise
