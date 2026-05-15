from beanie import Document, PydanticObjectId, DecimalAnnotation
from pydantic import Field
from decimal import Decimal

from datetime import datetime
from typing import Optional, List
from enum import Enum


class UnitEventEnum(str, Enum):
    HTTT = "HTTT"
    HTSK = "HTSK"


class UnitEvent(Document):
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    point: DecimalAnnotation = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        le=Decimal("10"),
    )
    type: UnitEventEnum
    event_start: Optional[datetime] = None
    event_end: Optional[datetime] = None
    registration_start: Optional[datetime] = None
    registration_end: Optional[datetime] = None
    is_student_registration: bool = Field(default=False)
    limit_student_registration_in_one_unit: int = Field(default=10000)
    semesterId: PydanticObjectId
    listUnitId: List[PydanticObjectId] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: PydanticObjectId
    deleted_at: Optional[datetime] = None

    class Settings:
        name = "unit_events"
