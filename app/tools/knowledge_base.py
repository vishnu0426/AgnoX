import asyncpg
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Knowledge base search tools"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.faqs = [
            {
                "question": "How do I reset my password?",
                "answer": "You can reset your password by visiting our website and clicking 'Forgot Password', or I can send you a reset link via email."
            },
            {
                "question": "What are your business hours?",
                "answer": "Our customer service is available 24/7. Our business offices are open Monday-Friday, 9 AM to 6 PM EST."
            },
            {
                "question": "How do I cancel my subscription?",
                "answer": "To cancel your subscription, you can do it online in your account settings, or I can help you cancel it right now."
            },
            {
                "question": "What payment methods do you accept?",
                "answer": "We accept credit cards (Visa, Mastercard, American Express), debit cards, PayPal, and bank transfers."
            },
        ]
    
    async def search_knowledge_base(self, query: str) -> str:
        """
        Search knowledge base for relevant information
        
        Args:
            query: Search query
            
        Returns:
            Relevant information or "not found" message
        """
        try:
            query_lower = query.lower()
            
            # Simple keyword matching
            for faq in self.faqs:
                if any(word in query_lower for word in faq["question"].lower().split()):
                    return faq["answer"]
            
            # Try database search if available
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchrow(
                    """
                    SELECT title, content
                    FROM knowledge_base
                    WHERE to_tsvector('english', title || ' ' || content) 
                          @@ plainto_tsquery('english', $1)
                    LIMIT 1
                    """,
                    query
                )
                
                if result:
                    return result['content']
            
            return "I don't have specific information about that in my knowledge base, but I can connect you with a specialist who can help."
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return "I'm having trouble accessing information right now."