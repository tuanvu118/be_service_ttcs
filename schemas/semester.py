from datetime import datetime
from typing import Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict


class SemesterBase(BaseModel):
    name: str
    academic_year: str
    start_date: datetime
    end_date: datetime
    is_active: bool = False


class SemesterCreate(SemesterBase):
    pass


class SemesterUpdate(BaseModel):
    name: Optional[str] = None
    academic_year: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None


class SemesterRead(SemesterBase):
    id: PydanticObjectId
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SemesterListResponse(BaseModel):
    items: list[SemesterRead]
    total: int
    skip: int
    limit: int
