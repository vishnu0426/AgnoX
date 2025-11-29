import asyncpg
import logging
from typing import Dict, Optional
from textblob import TextBlob

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Analyze customer sentiment from speech and text"""
    
    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        self.db_pool = db_pool
        self.negative_keywords = [
            'angry', 'frustrated', 'upset', 'terrible', 'worst',
            'horrible', 'useless', 'awful', 'hate', 'cancel', 'sick',
            'disgusted', 'unhappy', 'disappointed', 'annoyed'
        ]
        self.escalation_keywords = [
            'manager', 'supervisor', 'complaint', 'sue', 'lawyer',
            'unacceptable', 'ridiculous', 'demanding', 'refund', 'money back'
        ]
    
    def analyze_text(self, text: str) -> Dict:
        """
        Analyze sentiment of text using TextBlob
        
        Args:
            text: Text to analyze
            
        Returns:
            Sentiment analysis results
        """
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity  # -1 to 1
            subjectivity = blob.sentiment.subjectivity  # 0 to 1
            
            # Determine sentiment label
            if polarity > 0.1:
                label = "positive"
            elif polarity < -0.1:
                label = "negative"
            else:
                label = "neutral"
            
            # Check for escalation keywords
            text_lower = text.lower()
            escalation_detected = any(
                keyword in text_lower for keyword in self.escalation_keywords
            )
            
            # Check for strong negative keywords
            strong_negative = any(
                keyword in text_lower for keyword in self.negative_keywords
            )
            
            confidence = abs(polarity)
            
            return {
                "label": label,
                "polarity": polarity,
                "subjectivity": subjectivity,
                "confidence": confidence,
                "escalation_detected": escalation_detected,
                "strong_negative": strong_negative,
                "recommend_transfer": escalation_detected or (label == "negative" and confidence > 0.6)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {
                "label": "neutral",
                "polarity": 0,
                "confidence": 0,
                "escalation_detected": False
            }
    
    async def analyze_conversation(
        self, 
        session_id: int,
        window_size: int = 5
    ) -> Dict:
        """
        Analyze recent conversation sentiment
        
        Args:
            session_id: Call session ID
            window_size: Number of recent messages to analyze
            
        Returns:
            Overall sentiment analysis
        """
        if not self.db_pool:
            return {"label": "neutral"}
        
        try:
            async with self.db_pool.acquire() as conn:
                # Get recent customer messages
                messages = await conn.fetch(
                    """
                    SELECT text
                    FROM transcripts
                    WHERE session_id = $1
                    AND speaker = 'customer'
                    ORDER BY timestamp DESC
                    LIMIT $2
                    """,
                    session_id,
                    window_size
                )
                
                if not messages:
                    return {"label": "neutral"}
                
                # Analyze combined text
                combined_text = " ".join([msg['text'] for msg in messages])
                sentiment = self.analyze_text(combined_text)
                
                # Log if negative
                if sentiment['label'] == 'negative':
                    logger.warning(
                        f"Negative sentiment detected in session {session_id}: "
                        f"polarity={sentiment['polarity']:.2f}"
                    )
                
                return sentiment
                
        except Exception as e:
            logger.error(f"Error analyzing conversation: {e}")
            return {"label": "neutral"}
    
    async def should_escalate(self, session_id: int) -> bool:
        """
        Determine if conversation should be escalated to human
        
        Args:
            session_id: Call session ID
            
        Returns:
            True if escalation recommended
        """
        sentiment = await self.analyze_conversation(session_id)
        return sentiment.get('recommend_transfer', False)
