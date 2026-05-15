from datetime import datetime, timezone
from typing import List, Optional

from beanie import PydanticObjectId
from beanie.operators import In

from models.user_unit import UserUnit


class UserUnitRepo:
    async def create(self, user_unit: UserUnit) -> UserUnit:
        return await user_unit.insert()

    async def get_active(
        self,
        user_id: PydanticObjectId,
        unit_id: PydanticObjectId,
        semester_id: PydanticObjectId,
    ) -> Optional[UserUnit]:
        return await UserUnit.find_one(
            UserUnit.user_id == user_id,
            UserUnit.unit_id == unit_id,
            UserUnit.semester_id == semester_id,
            UserUnit.is_active == True,
        )

    async def list_active_by_unit(
        self,
        unit_id: PydanticObjectId,
        semester_id: PydanticObjectId,
    ) -> List[UserUnit]:
        return await UserUnit.find(
            UserUnit.unit_id == unit_id,
            UserUnit.semester_id == semester_id,
            UserUnit.is_active == True,
        ).to_list()

    async def list_active_by_unit_and_users(
        self,
        unit_id: PydanticObjectId,
        semester_id: PydanticObjectId,
        user_ids: List[PydanticObjectId],
    ) -> List[UserUnit]:
        if not user_ids:
            return []
        return await UserUnit.find(
            UserUnit.unit_id == unit_id,
            UserUnit.semester_id == semester_id,
            UserUnit.is_active == True,
            In(UserUnit.user_id, user_ids),
        ).to_list()

    async def count_distinct_members(self, unit_id: PydanticObjectId) -> int:
        """Counts unique active members across all semesters."""
        memberships = await UserUnit.find(
            UserUnit.unit_id == unit_id,
            UserUnit.is_active == True
        ).to_list()
        unique_user_ids = {m.user_id for m in memberships}
        return len(unique_user_ids)

    async def deactivate(self, user_unit: UserUnit) -> UserUnit:
        user_unit.is_active = False
        user_unit.left_at = datetime.now(timezone.utc)
        return await user_unit.save()
