import asyncpg
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TranscriptService:
    """Manages conversation transcripts with full-text search"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def save_transcript(
        self,
        session_id: int,
        speaker: str,
        text: str,
        confidence: float = 1.0,
        sentiment: Optional[str] = None
    ) -> bool:
        """
        Save a transcript entry
        
        Args:
            session_id: Call session ID
            speaker: Speaker identifier (customer, ai_agent, human_agent)
            text: Transcript text
            confidence: Transcription confidence (0-1)
            sentiment: Sentiment (positive, neutral, negative)
            
        Returns:
            True if successful
        """
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO transcripts 
                    (session_id, speaker, text, confidence, sentiment)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    session_id,
                    speaker,
                    text,
                    confidence,
                    sentiment
                )
                logger.debug(f"Saved transcript for session {session_id} from {speaker}")
                return True
            except Exception as e:
                logger.error(f"Error saving transcript: {e}")
                return False
    
    async def get_session_transcript(
        self, 
        session_id: int
    ) -> List[Dict]:
        """Get complete transcript for a session"""
        async with self.db_pool.acquire() as conn:
            try:
                transcripts = await conn.fetch(
                    """
                    SELECT speaker, text, timestamp, confidence, sentiment
                    FROM transcripts
                    WHERE session_id = $1
                    ORDER BY timestamp ASC
                    """,
                    session_id
                )
                return [dict(t) for t in transcripts]
            except Exception as e:
                logger.error(f"Error getting transcript: {e}")
                return []
    
    async def search_transcripts(
        self,
        search_text: str,
        limit: int = 10
    ) -> List[Dict]:
        """Search transcripts by text using full-text search"""
        async with self.db_pool.acquire() as conn:
            try:
                results = await conn.fetch(
                    """
                    SELECT 
                        t.transcript_id,
                        t.session_id,
                        t.speaker,
                        t.text,
                        t.timestamp,
                        cs.customer_id,
                        c.phone_number,
                        c.name as customer_name
                    FROM transcripts t
                    JOIN call_sessions cs ON t.session_id = cs.session_id
                    JOIN customers c ON cs.customer_id = c.customer_id
                    WHERE to_tsvector('english', t.text) @@ plainto_tsquery('english', $1)
                    ORDER BY t.timestamp DESC
                    LIMIT $2
                    """,
                    search_text,
                    limit
                )
                return [dict(r) for r in results]
            except Exception as e:
                logger.error(f"Error searching transcripts: {e}")
                return []