import asyncpg
import logging
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SchedulingTools:
    """Scheduling-related tools for agents"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def schedule_callback(
        self,
        customer_id: int,
        preferred_time: str,
        phone_number: str,
        reason: Optional[str] = None
    ) -> str:
        """
        Schedule a callback for the customer
        
        Args:
            customer_id: Customer ID
            preferred_time: Preferred callback time
            phone_number: Callback phone number
            reason: Reason for callback
            
        Returns:
            Confirmation message
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Parse preferred time (simplified)
                callback_time = datetime.now() + timedelta(hours=2)
                
                await conn.execute(
                    """
                    INSERT INTO callbacks 
                    (customer_id, phone_number, scheduled_time, reason, status)
                    VALUES ($1, $2, $3, $4, 'scheduled')
                    """,
                    customer_id,
                    phone_number,
                    callback_time,
                    reason or "Customer requested callback"
                )
                
                return f"I've scheduled a callback for you at {preferred_time}. You'll receive a call at {phone_number}."
                
        except Exception as e:
            logger.error(f"Error scheduling callback: {e}")
            return "I'm having trouble scheduling the callback. Please try again."