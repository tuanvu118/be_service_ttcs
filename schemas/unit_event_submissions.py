from pydantic import AliasChoices, BaseModel, ConfigDict, Field, computed_field, field_validator
from beanie import PydanticObjectId
from datetime import datetime
from models.unit_event_submissions import UnitEventSubmissionStatus
from typing import List, Union
from schemas.unit import UnitBase
from schemas.users import UserRead


class UnitEventSubmissionCreate(BaseModel):
    unitEventId: PydanticObjectId
    unitId: PydanticObjectId
    content: str
    evidenceUrl: str

class UnitEventSubmissionResponse(BaseModel):
    unitEventId: PydanticObjectId
    unitId: PydanticObjectId
    content: str
    evidenceUrl: str
    status: UnitEventSubmissionStatus
    submittedAt: datetime

    model_config = ConfigDict(from_attributes=True)


class UnitEventSubmissionUpdate(BaseModel):
    content: str | None = None
    evidenceUrl: str | None = None


class UnitEventSubmissionStatusUpdate(BaseModel):
    unit_event_submission_id: PydanticObjectId
    status: UnitEventSubmissionStatus


class UnitEventSubmissionMemberCreate(BaseModel):
    unitEventId: PydanticObjectId
    unitId: PydanticObjectId
    content: str    
    list_MSV: List[str] | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "list_MSV", "list_msv", "listMsv", "list_user_id", "listUserId"
        ),
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError("Nội dung phản hồi không được để trống")
        return text


class UnitEventSubmissionMemberUpdate(BaseModel):
    content: str
    evidenceUrl: str | None = None
    list_MSV: List[str] | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "list_MSV", "list_msv", "listMsv", "list_user_id", "listUserId"
        ),
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError("Nội dung phản hồi không được để trống")
        return text


class UnitEventSubmissionMemberResponse(BaseModel):
    unitEventId: PydanticObjectId
    unitId: PydanticObjectId
    content: str
    evidenceUrl: str
    status: UnitEventSubmissionStatus
    submittedAt: datetime
    list_user_id: List[Union[PydanticObjectId, str]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def list_MSV(self) -> List[str]:
        """Trùng dữ liệu với list_user_id (MSV hoặc id), tiện cho client đọc một key thống nhất."""
        return [str(x) for x in self.list_user_id]


class UnitEventSubmissionWithUnitResponse(BaseModel):
    id: PydanticObjectId
    unitEventId: PydanticObjectId
    unit: UnitBase
    content: str
    evidenceUrl: str
    status: UnitEventSubmissionStatus
    submittedAt: datetime


class UnitEventSubmissionHTSKListItemResponse(BaseModel):
    user: UserRead
    unit_name: str
    checkIn: bool


class StudentRegistrationInfo(BaseModel):
    is_registered: bool
    unit_id: PydanticObjectId | None = None
    unit_name: str | None = None
    check_in: bool | None = None


class HTSKStudentOverviewResponse(BaseModel):
    unit_event_id: PydanticObjectId
    title: str
    description: str | None = None
    location: str | None = None
    event_start: datetime | None = None
    event_end: datetime | None = None
    registration_start: datetime | None = None
    registration_end: datetime | None = None
    unit_id: PydanticObjectId
    unit_name: str
    is_student_registration: bool
    submission_id: PydanticObjectId
    submission_status: UnitEventSubmissionStatus
    slot_limit: int
    slot_used: int
    slot_remaining: int
    is_registration_open: bool
    can_register: bool
    my_registration: StudentRegistrationInfo


class HTSKStudentRegisterRequest(BaseModel):
    unit_event_id: PydanticObjectId
    unit_id: PydanticObjectId


class HTSKStudentRegisterResponse(BaseModel):
    member_id: PydanticObjectId
    unit_event_id: PydanticObjectId
    submission_id: PydanticObjectId
    slot_used: int
    slot_remaining: int
    registered_at: datetime

