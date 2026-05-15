from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from decimal import Decimal

from models.unit_event import UnitEventEnum
from beanie import PydanticObjectId
from datetime import datetime, timezone
from pydantic import ConfigDict
from schemas.unit import UnitBase, UnitRead


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class UnitEventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    point: Decimal = Field(default=Decimal("0"))
    type: UnitEventEnum
    event_start: datetime
    event_end: datetime
    registration_start: Optional[datetime] = None
    registration_end: Optional[datetime] = None
    semesterId: Optional[PydanticObjectId] = None
    listUnitId: List[PydanticObjectId] = Field(default_factory=list)
    is_student_registration: bool = Field(default=False)
    limit_student_registration_in_one_unit: int = Field(default=10000)
    @field_validator(
        "event_start",
        "event_end",
        "registration_start",
        "registration_end",
        mode="before",
    )
    @classmethod
    def normalize_datetimes(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _ensure_utc(value)

class UnitEventResponse(BaseModel):
    id: PydanticObjectId
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    point: Decimal = Field(default=Decimal("0"))
    type: UnitEventEnum
    event_start: Optional[datetime] = None
    event_end: Optional[datetime] = None
    registration_start: Optional[datetime] = None
    registration_end: Optional[datetime] = None
    is_student_registration: bool = Field(default=False)
    limit_student_registration_in_one_unit: int = Field(default=10000)
    semesterId: PydanticObjectId
    created_at: datetime
    created_by: PydanticObjectId
    assigned_units: List[UnitRead]

    @field_validator(
        "event_start",
        "event_end",
        "registration_start",
        "registration_end",
        "created_at",
        mode="before",
    )
    @classmethod
    def normalize_response_datetimes(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _ensure_utc(value)

    model_config = ConfigDict(from_attributes=True)

class UnitEventResponseByUnitId(BaseModel):
    id: PydanticObjectId
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    point: Decimal = Field(default=Decimal("0"))
    type: UnitEventEnum
    event_start: Optional[datetime] = None
    event_end: Optional[datetime] = None
    registration_start: Optional[datetime] = None
    registration_end: Optional[datetime] = None
    semesterId: PydanticObjectId
    is_student_registration: bool = Field(default=False)
    limit_student_registration_in_one_unit: int = Field(default=10000)
    created_at: datetime

    @field_validator(
        "event_start",
        "event_end",
        "registration_start",
        "registration_end",
        "created_at",
        mode="before",
    )
    @classmethod
    def normalize_summary_datetimes(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _ensure_utc(value)

class UnitEventUpdate(BaseModel):
    semesterId: Optional[PydanticObjectId] = None
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    point: Optional[Decimal] = None
    event_start: Optional[datetime] = None
    event_end: Optional[datetime] = None
    registration_start: Optional[datetime] = None
    registration_end: Optional[datetime] = None
    listUnitId: Optional[List[PydanticObjectId]] = None
    is_student_registration: Optional[bool] = None
    limit_student_registration_in_one_unit: Optional[int] = None
    @field_validator(
        "event_start",
        "event_end",
        "registration_start",
        "registration_end",
        mode="before",
    )
    @classmethod
    def normalize_optional_datetimes(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _ensure_utc(value)

class UnitEventPaginationResponse(BaseModel):
    items: List[UnitEventResponse]
    total: int
