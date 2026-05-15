from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from typing import Optional, List
from beanie import PydanticObjectId

class EventTimeSchema(BaseModel):
    start: datetime
    end: datetime

    @field_validator("start", "end", mode="before")
    @classmethod
    def ensure_utc(cls, v):
        if isinstance(v, str):
            # Handle 'Z' and ensure aware UTC
            dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

class OrganizationInfoSchema(BaseModel):
    id: str
    name: str

class EventPromotionBase(BaseModel):
    title: str
    description: str
    time: Optional[EventTimeSchema] = None
    semester_id: Optional[PydanticObjectId] = None
    image_url: Optional[str] = None
    external_links: List[str] = []

class EventPromotionCreate(EventPromotionBase):
    pass

class EventPromotionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    time: Optional[EventTimeSchema] = None
    image_url: Optional[str] = None
    external_links: Optional[List[str]] = None

class EventPromotionStatusUpdate(BaseModel):
    status: str  # DA_DUYET | TU_CHOI
    rejected_reason: Optional[str] = None

class EventPromotionRead(EventPromotionBase):
    id: PydanticObjectId
    status: str
    organization: Optional[OrganizationInfoSchema] = None
    rejected_reason: Optional[str] = None
    unit_id: Optional[PydanticObjectId] = None
    semester_id: Optional[PydanticObjectId] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def ensure_read_utc(cls, v):
        if isinstance(v, str):
            dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

class EventPromotionPaginationResponse(BaseModel):
    items: List[EventPromotionRead]
    total: int
