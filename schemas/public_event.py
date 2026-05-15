from datetime import datetime, timezone
from typing import Optional, List

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator


from models.public_event import EventFormField


class PublicEventBase(BaseModel):
    title: str
    description: str
    image_url: Optional[str] = None
    point: float = 0

    registration_start: datetime
    registration_end: datetime

    event_start: datetime
    event_end: datetime
    location: Optional[str] = None
    max_participants: int = Field(default=0, ge=0)

    form_fields: List[EventFormField] = []

    @field_validator("registration_start", "registration_end", "event_start", "event_end", mode="before", check_fields=False)
    @classmethod
    def force_utc_base(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class PublicEventCreate(PublicEventBase):
    title: str = Field(min_length=5, max_length=255)
    max_participants: int = Field(default=0, ge=0)
    semester_id: Optional[PydanticObjectId] = None


class PublicEventUpdate(BaseModel):
    semester_id: Optional[PydanticObjectId] = None
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = None
    image_url: Optional[str] = None
    point: Optional[float] = None

    registration_start: Optional[datetime] = None
    registration_end: Optional[datetime] = None

    event_start: Optional[datetime] = None
    event_end: Optional[datetime] = None
    location: Optional[str] = None
    max_participants: Optional[int] = Field(None, ge=0)

    form_fields: Optional[List[EventFormField]] = None


class PublicEventRead(PublicEventBase):
    id: PydanticObjectId
    semester_id: PydanticObjectId
    created_at: datetime
    current_participants: int = 0

    @field_validator("created_at", mode="before", check_fields=False)
    @classmethod
    def force_utc_read(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    model_config = ConfigDict(from_attributes=True)


class PublicEventSummary(BaseModel):
    id: PydanticObjectId
    title: str
    event_start: Optional[datetime] = None
    location: Optional[str] = None

    @field_validator("event_start", mode="before", check_fields=False)
    @classmethod
    def force_utc_summary(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    model_config = ConfigDict(from_attributes=True)


class PublicEventPaginationResponse(BaseModel):
    items: List[PublicEventRead]
    total: int
