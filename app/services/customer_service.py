import asyncpg
import logging
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class CustomerService:
    """Customer data operations"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def get_or_create_customer(
        self,
        phone_number: str,
        name: Optional[str] = None
    ) -> Dict:
        """
        Get existing customer or create new one - Step 3
        
        Args:
            phone_number: Customer's phone number
            name: Customer's name (auto-generated if not provided)
            
        Returns:
            Customer record with customer_id
        """
        async with self.db_pool.acquire() as conn:
            try:
                # Use ON CONFLICT to handle race conditions
                customer = await conn.fetchrow(
                    """
                    INSERT INTO customers (phone_number, name, created_at, updated_at)
                    VALUES ($1, $2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (phone_number)
                    DO UPDATE SET 
                        updated_at = CURRENT_TIMESTAMP,
                        name = CASE 
                            WHEN customers.name LIKE 'Customer-%' AND $2 NOT LIKE 'Customer-%' 
                            THEN $2 
                            ELSE customers.name 
                        END
                    RETURNING *
                    """,
                    phone_number,
                    name or f"Customer-{phone_number[-4:]}"
                )
                
                result = dict(customer)
                action = "created" if customer['created_at'] == customer['updated_at'] else "updated"
                logger.info(
                    f"✅ Customer {action}: ID={result['customer_id']}, "
                    f"Phone={phone_number}, Name={result['name']}"
                )
                
                return result
            except Exception as e:
                logger.error(f"❌ Error in get_or_create_customer for {phone_number}: {e}")
                raise
    
    async def get_customer_info(self, phone_number: str) -> Optional[Dict]:
        """
        Get customer information with call statistics - Step 2
        
        Args:
            phone_number: Customer's phone number
            
        Returns:
            Customer info with total_calls and last_call_time, or None if not found
        """
        async with self.db_pool.acquire() as conn:
            try:
                customer = await conn.fetchrow(
                    """
                    SELECT 
                        c.customer_id,
                        c.phone_number,
                        c.name,
                        c.email,
                        c.created_at,
                        c.updated_at,
                        COUNT(cs.session_id) as total_calls,
                        MAX(cs.start_time) as last_call_time,
                        AVG(cs.duration_seconds) as avg_call_duration,
                        COUNT(CASE WHEN cs.handled_by = 'ai' THEN 1 END) as ai_handled_calls,
                        COUNT(CASE WHEN cs.handled_by = 'human' THEN 1 END) as human_handled_calls,
                        AVG(CASE 
                            WHEN cs.sentiment = 'positive' THEN 1
                            WHEN cs.sentiment = 'neutral' THEN 0
                            WHEN cs.sentiment = 'negative' THEN -1
                            ELSE 0
                        END) as avg_sentiment_score
                    FROM customers c
                    LEFT JOIN call_sessions cs ON c.customer_id = cs.customer_id
                    WHERE c.phone_number = $1
                    GROUP BY c.customer_id
                    """,
                    phone_number
                )
                
                if customer:
                    result = dict(customer)
                    logger.info(
                        f"📊 Customer found: ID={result['customer_id']}, "
                        f"Calls={result['total_calls']}, "
                        f"Last Call={result.get('last_call_time', 'Never')}"
                    )
                    return result
                else:
                    logger.info(f"🆕 No existing customer found for {phone_number}")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Error in get_customer_info for {phone_number}: {e}")
                return None
    
    async def get_customer_by_id(self, customer_id: int) -> Optional[Dict]:
        """
        Get customer by ID
        
        Args:
            customer_id: Customer's unique ID
            
        Returns:
            Customer info or None if not found
        """
        async with self.db_pool.acquire() as conn:
            try:
                customer = await conn.fetchrow(
                    """
                    SELECT * FROM customers
                    WHERE customer_id = $1
                    """,
                    customer_id
                )
                return dict(customer) if customer else None
            except Exception as e:
                logger.error(f"❌ Error in get_customer_by_id for ID {customer_id}: {e}")
                return None
    
    async def get_call_history(
        self,
        customer_id: int,
        limit: int = 5
    ) -> List[Dict]:
        """
        Get customer call history - Used in Step 4 for context building
        
        Args:
            customer_id: Customer's unique ID
            limit: Maximum number of calls to retrieve
            
        Returns:
            List of call session records with details
        """
        async with self.db_pool.acquire() as conn:
            try:
                # Validate limit
                limit = max(1, min(limit, 50))  # Between 1 and 50
                
                history = await conn.fetch(
                    """
                    SELECT
                        cs.session_id,
                        cs.start_time,
                        cs.end_time,
                        cs.duration_seconds,
                        cs.handled_by,
                        cs.sentiment,
                        cs.transfer_count,
                        cs.call_metadata->>'summary' as summary,
                        cs.call_metadata->>'transfer_reason' as transfer_reason,
                        cs.call_metadata->>'resolution_status' as resolution_status,
                        a.name as agent_name,
                        a.agent_id
                    FROM call_sessions cs
                    LEFT JOIN agents a ON cs.agent_id = a.agent_id
                    WHERE cs.customer_id = $1
                    ORDER BY cs.start_time DESC
                    LIMIT $2
                    """,
                    customer_id,
                    limit
                )
                
                result = [dict(row) for row in history]
                logger.info(
                    f"📜 Retrieved {len(result)} call history records for customer {customer_id}"
                )
                return result
                
            except Exception as e:
                logger.error(f"❌ Error in get_call_history for customer {customer_id}: {e}")
                return []
    
    async def create_session(
        self,
        customer_id: int,
        room_name: str
    ) -> int:
        """
        Create new call session - Step 6
        
        Args:
            customer_id: Customer's unique ID
            room_name: LiveKit room name
            
        Returns:
            New session_id
        """
        async with self.db_pool.acquire() as conn:
            try:
                session = await conn.fetchrow(
                    """
                    INSERT INTO call_sessions
                    (customer_id, room_name, handled_by, call_metadata, start_time)
                    VALUES ($1, $2, 'ai', '{}'::jsonb, CURRENT_TIMESTAMP)
                    RETURNING session_id
                    """,
                    customer_id,
                    room_name
                )
                
                session_id = session['session_id']
                logger.info(
                    f"✅ Call session created: ID={session_id}, "
                    f"Customer={customer_id}, Room={room_name}"
                )
                return session_id
                
            except Exception as e:
                logger.error(
                    f"❌ Error in create_session for customer {customer_id}: {e}"
                )
                raise
    
    async def update_session_end(
        self,
        session_id: int,
        metadata: Dict
    ):
        """
        Update session when call ends - Step 13
        
        Args:
            session_id: Session ID to update
            metadata: Additional metadata to merge
        """
        async with self.db_pool.acquire() as conn:
            try:
                result = await conn.fetchrow(
                    """
                    UPDATE call_sessions
                    SET 
                        end_time = CURRENT_TIMESTAMP,
                        duration_seconds = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - start_time))::INTEGER,
                        call_metadata = call_metadata || $1::jsonb
                    WHERE session_id = $2
                    RETURNING session_id, duration_seconds, handled_by
                    """,
                    metadata,
                    session_id
                )
                
                if result:
                    logger.info(
                        f"✅ Session ended: ID={result['session_id']}, "
                        f"Duration={result['duration_seconds']}s, "
                        f"Handled by={result['handled_by']}"
                    )
                else:
                    logger.warning(f"⚠️ Session {session_id} not found for update")
                    
            except Exception as e:
                logger.error(f"❌ Error in update_session_end for session {session_id}: {e}")
    
    async def update_session_metadata(
        self,
        session_id: int,
        metadata: Dict
    ):
        """
        Update session metadata without ending the call
        
        Args:
            session_id: Session ID to update
            metadata: Metadata to merge into existing metadata
        """
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    UPDATE call_sessions
                    SET call_metadata = call_metadata || $1::jsonb
                    WHERE session_id = $2
                    """,
                    metadata,
                    session_id
                )
                logger.info(f"✅ Session metadata updated for session {session_id}")
            except Exception as e:
                logger.error(
                    f"❌ Error in update_session_metadata for session {session_id}: {e}"
                )
    
    async def update_session_handler(
        self,
        session_id: int,
        handler_type: str,
        agent_id: Optional[int] = None
    ):
        """
        Update who is handling the call (AI or human)
        
        Args:
            session_id: Session ID to update
            handler_type: 'ai' or 'human'
            agent_id: Agent ID if human handler
        """
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    UPDATE call_sessions
                    SET 
                        handled_by = $1,
                        agent_id = $2,
                        transfer_count = CASE WHEN $1 = 'human' THEN transfer_count + 1 ELSE transfer_count END
                    WHERE session_id = $3
                    """,
                    handler_type,
                    agent_id,
                    session_id
                )
                logger.info(
                    f"✅ Session handler updated: session={session_id}, "
                    f"handler={handler_type}, agent_id={agent_id}"
                )
            except Exception as e:
                logger.error(
                    f"❌ Error in update_session_handler for session {session_id}: {e}"
                )
    
    async def update_customer(
        self,
        customer_id: int,
        **kwargs
    ) -> bool:
        """
        Update customer information
        
        Args:
            customer_id: Customer ID to update
            **kwargs: Fields to update (name, email)
            
        Returns:
            True if update successful, False otherwise
        """
        async with self.db_pool.acquire() as conn:
            try:
                fields = []
                values = []
                idx = 1
                
                # Only allow specific fields to be updated
                allowed_fields = ['name', 'email']
                for key, value in kwargs.items():
                    if key in allowed_fields and value is not None:
                        fields.append(f"{key} = ${idx}")
                        values.append(value)
                        idx += 1
                
                if not fields:
                    logger.warning(f"⚠️ No valid fields to update for customer {customer_id}")
                    return False
                
                values.append(customer_id)
                query = f"""
                    UPDATE customers
                    SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE customer_id = ${idx}
                    RETURNING customer_id, name, email
                """
                
                result = await conn.fetchrow(query, *values)
                
                if result:
                    logger.info(
                        f"✅ Customer updated: ID={result['customer_id']}, "
                        f"Name={result['name']}, Email={result['email']}"
                    )
                    return True
                else:
                    logger.warning(f"⚠️ Customer {customer_id} not found for update")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Error in update_customer for ID {customer_id}: {e}")
                return False
    
    async def get_customer_statistics(self, customer_id: int) -> Dict:
        """
        Get comprehensive statistics for a customer
        
        Args:
            customer_id: Customer's unique ID
            
        Returns:
            Dictionary of statistics
        """
        async with self.db_pool.acquire() as conn:
            try:
                stats = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) as total_calls,
                        AVG(duration_seconds) as avg_duration,
                        MAX(duration_seconds) as max_duration,
                        MIN(duration_seconds) as min_duration,
                        SUM(duration_seconds) as total_duration,
                        COUNT(CASE WHEN handled_by = 'ai' THEN 1 END) as ai_handled,
                        COUNT(CASE WHEN handled_by = 'human' THEN 1 END) as human_handled,
                        AVG(transfer_count) as avg_transfers,
                        COUNT(CASE WHEN sentiment = 'positive' THEN 1 END) as positive_calls,
                        COUNT(CASE WHEN sentiment = 'neutral' THEN 1 END) as neutral_calls,
                        COUNT(CASE WHEN sentiment = 'negative' THEN 1 END) as negative_calls
                    FROM call_sessions
                    WHERE customer_id = $1 AND end_time IS NOT NULL
                    """,
                    customer_id
                )
                
                return dict(stats) if stats else {}
                
            except Exception as e:
                logger.error(
                    f"❌ Error in get_customer_statistics for customer {customer_id}: {e}"
                )
                return {}