from abc import ABC, abstractmethod
from typing import Dict, Optional
import asyncpg


class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.session_id: Optional[int] = None
        self.customer_id: Optional[int] = None
        self.queue_id: Optional[int] = None
    
    @abstractmethod
    async def entrypoint(self, ctx):
        """Agent entrypoint called by LiveKit"""
        pass
    
    @abstractmethod
    async def handle_transfer(self, reason: str) -> Dict:
        """Handle transfer to human agent"""
        pass
    
    async def cleanup(self):
        """Cleanup resources when agent stops"""
        pass
