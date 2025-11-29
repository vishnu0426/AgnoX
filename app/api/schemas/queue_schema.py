from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class QueueEntryResponse(BaseModel):
    queue_id: int
    customer_phone: str
    room_name: str
    status: str
    priority: int
    queue_time: datetime
    assigned_agent_id: Optional[int] = None
    wait_seconds: float
    
    class Config:
        from_attributes = True


class QueueStatusResponse(BaseModel):
    waiting_calls: int
    active_calls: int
    avg_wait_time: float
    max_wait_time: float
    online_agents: int
    busy_agents: int
    timestamp: str


class QueueStatsResponse(BaseModel):
    entries: List[QueueEntryResponse]
    stats: QueueStatusResponse
