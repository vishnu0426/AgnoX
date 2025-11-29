from enum import Enum


class QueueStatus(str, Enum):
    """Queue entry status"""
    WAITING = "waiting"
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class AgentStatus(str, Enum):
    """Agent availability status"""
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"
    BREAK = "break"


class CallHandledBy(str, Enum):
    """Call handler type"""
    AI = "ai"
    HUMAN = "human"


class TransferType(str, Enum):
    """Call transfer type"""
    WARM = "warm"
    COLD = "cold"


class SentimentLabel(str, Enum):
    """Sentiment classification"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"