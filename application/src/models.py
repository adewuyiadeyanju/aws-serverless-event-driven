from pydantic import BaseModel, Field


class OperationalEvent(BaseModel):
    site_id: str = Field(min_length=1, max_length=100)
    event_type: str = Field(min_length=1, max_length=100)
    severity: str = Field(min_length=1, max_length=20)
    message: str = Field(min_length=1, max_length=500)