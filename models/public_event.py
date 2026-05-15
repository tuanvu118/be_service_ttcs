from datetime import datetime, timezone
from typing import Optional, List

from beanie import Document, PydanticObjectId
from pydantic import Field, BaseModel


class EventFormField(BaseModel):
    id: str
    label: str
    field_type: str  # text | textarea | number | select | radio | checkbox
    required: bool = False
    options: Optional[List[str]] = None


class PublicEvent(Document):
    id: PydanticObjectId = Field(default_factory=PydanticObjectId)
    title: str
    description: str
    image_url: Optional[str] = None
    point: float = 0
    location: Optional[str] = None
    max_participants: int = 200
    registration_start: datetime
    registration_end: datetime
    event_start: datetime
    event_end: datetime
    semester_id: PydanticObjectId
    form_fields: List[EventFormField] = Field(default_factory=list)


    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


    class Settings:
        name = "public_events"