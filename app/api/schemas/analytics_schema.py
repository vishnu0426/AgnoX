from pydantic import BaseModel, Field
from typing import Optional


class RealtimeMetricsResponse(BaseModel):
    calls_waiting: int
    calls_active: int
    avg_wait_time: float
    agents_available: int
    agents_busy: int
    timestamp: str


class CallMetricsResponse(BaseModel):
    total_calls: int
    avg_call_duration: float
    ai_handled: int
    human_handled: int
    transfers: int


class AgentPerformanceResponse(BaseModel):
    name: str
    total_calls: int
    avg_call_duration: float
    total_talk_time: float