from enum import Enum

from pydantic import BaseModel, Field


class EventSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OperationalEvent(BaseModel):
    site_id: str = Field(min_length=1, max_length=100)
    event_type: str = Field(min_length=1, max_length=100)
    severity: EventSeverity
    message: str = Field(min_length=1, max_length=500)