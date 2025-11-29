from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class AgentResponse(BaseModel):
    agent_id: int
    name: str
    phone_number: Optional[str] = None
    status: str
    current_call_count: int
    max_concurrent_calls: int
    skills: Optional[Dict] = None
    
    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    agents: List[AgentResponse]
    total: int


class AgentStatusUpdate(BaseModel):
    status: str = Field(..., description="Agent status: online, busy, offline, break")