from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CallSessionResponse(BaseModel):
    session_id: int
    customer_id: int
    room_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    handled_by: str
    sentiment: Optional[str] = None
    transfer_count: int = 0
    
    class Config:
        from_attributes = True


class TranscriptEntry(BaseModel):
    speaker: str
    text: str
    timestamp: datetime
    confidence: float
    sentiment: Optional[str] = None


class CallListResponse(BaseModel):
    calls: List[CallSessionResponse]
    total: int
    page: int
    page_size: int


class TransferRequest(BaseModel):
    agent_id: int = Field(..., description="Target agent ID")
    transfer_type: str = Field("warm", description="Transfer type: warm or cold")
    reason: str = Field(..., description="Reason for transfer")


class TransferResponse(BaseModel):
    success: bool
    message: str
    agent_id: Optional[int] = None
    transfer_type: str