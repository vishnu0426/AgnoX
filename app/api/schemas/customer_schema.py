from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CustomerResponse(BaseModel):
    customer_id: int
    phone_number: str
    name: Optional[str] = None
    email: Optional[str] = None
    total_calls: int = 0
    last_call_time: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class CallHistoryEntry(BaseModel):
    session_id: int
    start_time: datetime
    duration_seconds: Optional[int] = None
    handled_by: str
    summary: Optional[str] = None
    agent_name: Optional[str] = None


class CustomerHistoryResponse(BaseModel):
    customer: CustomerResponse
    history: List[CallHistoryEntry]
