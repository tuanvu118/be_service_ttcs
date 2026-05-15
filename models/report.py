from datetime import datetime, date
from typing import List, Optional
from beanie import Document, PydanticObjectId
from pydantic import Field, BaseModel


class InternalEvent(BaseModel):
    id: PydanticObjectId = Field(default_factory=PydanticObjectId)
    title: str
    description: Optional[str] = None
    evidence_url: Optional[str] = None
    location: Optional[str] = None
    participant_count: Optional[int] = None
    event_date: Optional[date] = None


class Report(Document):
    unit_id: PydanticObjectId
    month: int
    year: int
    semester_id: PydanticObjectId

    unit_event_ids: List[PydanticObjectId] = Field(default_factory=list)
    internal_events: List[InternalEvent] = Field(default_factory=list)

    status: str = Field(default="CHUA_NOP")
    note: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "reports"
