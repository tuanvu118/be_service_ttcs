from datetime import datetime, date, timezone
from typing import Optional, List

from beanie import PydanticObjectId
from pydantic import BaseModel, field_validator


class InternalEventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    evidence_url: Optional[str] = None
    location: Optional[str] = None
    participant_count: Optional[int] = None
    event_date: Optional[date] = None

class InternalEventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    evidence_url: Optional[str] = None
    location: Optional[str] = None
    participant_count: Optional[int] = None
    event_date: Optional[date] = None

class InternalEventRead(BaseModel):
    id: PydanticObjectId
    title: str
    description: Optional[str] = None
    evidence_url: Optional[str] = None
    location: Optional[str] = None
    participant_count: Optional[int] = None
    event_date: Optional[date] = None



class InternalSummary(BaseModel):
    id: PydanticObjectId
    title: str

class UnitEventSummary(BaseModel):
    id: PydanticObjectId
    title: str
    type: str
    point: float = 0
    created_at: datetime

    @field_validator("created_at", mode="before", check_fields=False)
    @classmethod
    def force_utc_ue(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

class ReportBase(BaseModel):
    month: int
    year: int

class ReportSummary(ReportBase):
    unit_id: PydanticObjectId
    semester_id: PydanticObjectId
    id: PydanticObjectId
    status: str
    updated_at: datetime
    total_activities: int = 0

    @field_validator("updated_at", mode="before", check_fields=False)
    @classmethod
    def force_utc_update(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

class ReportDetail(ReportBase):
    id: PydanticObjectId
    unit_id: PydanticObjectId
    status: str
    note: Optional[str]
    updated_at: datetime
    unit_events: List[UnitEventSummary] = []
    internal_events: List[InternalEventRead] = []

    @field_validator("updated_at", mode="before", check_fields=False)
    @classmethod
    def force_utc_update_detail(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

class ReportPaginationResponse(BaseModel):
    items: List[ReportSummary]
    total: int
    pending: int = 0
    approved: int = 0
    rejected: int = 0
