from datetime import datetime
from typing import List

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict


class RoleRead(BaseModel):
    id: PydanticObjectId
    code: str

    model_config = ConfigDict(from_attributes=True)


class AssignRoleRequest(BaseModel):
    target_user_id: PydanticObjectId
    role_id: PydanticObjectId
    unit_id: PydanticObjectId
    semester_id: PydanticObjectId | None = None


class UserRoleAssignmentRead(BaseModel):
    id: PydanticObjectId
    user_id: PydanticObjectId
    role_id: PydanticObjectId
    role_code: str
    unit_id: PydanticObjectId
    semester_id: PydanticObjectId
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRoleAssignmentListResponse(BaseModel):
    items: List[UserRoleAssignmentRead]
    total: int
