import re
from datetime import datetime
from typing import List, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, field_validator

from schemas.auth import UnitRole


class UserBase(BaseModel):
    full_name: str
    email: str
    student_id: str
    class_name: str
    avatar_url: Optional[str] = None
    date_of_birth: Optional[datetime] = None

    @field_validator("email")
    def validate_email(cls, value: str):
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_regex, value):
            raise ValueError("Email khong hop le")
        return value


class UserRead(UserBase):
    id: PydanticObjectId

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    student_id: Optional[str] = None
    class_name: Optional[str] = None
    avatar_url: Optional[str] = None
    date_of_birth: Optional[datetime] = None

    @field_validator("email")
    def validate_email(cls, value: Optional[str]):
        if not value or value.strip() == "":
            return None
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_regex, value):
            raise ValueError("Email khong hop le")
        return value.strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: Optional[str]):
        if value is None:
            return value
        if len(value) < 6:
            raise ValueError("Mat khau phai >= 6 ky tu")
        return value


class UserResponse(UserBase):
    pass


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str):
        if len(value) < 6:
            raise ValueError("Mat khau phai >= 6 ky tu")
        return value


class UserProfileResponse(UserRead):
    is_active: bool
    roles: List[UnitRole]


class UserListResponse(BaseModel):
    items: List[UserRead]
    total: int
    skip: int
    limit: int


class ParticipatedEvent(BaseModel):
    event_id: PydanticObjectId
    title: str
    event_start: datetime
    point: float
    checked_in: bool


class UserEventStatsResponse(BaseModel):
    total_points: float
    participated_events: List[ParticipatedEvent]


class UserSemesterPoint(BaseModel):
    semester_id: PydanticObjectId
    semester_name: str
    academic_year: str
    total_points: float
    is_active: bool = False


class UserPointsSummaryResponse(BaseModel):
    items: List[UserSemesterPoint]
    overall_total: float
