from typing import List, Optional

from beanie import PydanticObjectId

from models.users_roles import UserRole


class UserRoleRepo:
    async def get_by_id(self, assignment_id: PydanticObjectId) -> UserRole | None:
        return await UserRole.get(assignment_id)

    async def list_by_user(self, user_id: PydanticObjectId) -> List[UserRole]:
        return await UserRole.find(UserRole.user_id == user_id).to_list()

    async def list_active_by_user(
        self,
        user_id: PydanticObjectId,
        semester_id: Optional[PydanticObjectId] = None,
    ) -> List[UserRole]:
        filters = [
            UserRole.user_id == user_id,
            UserRole.is_active == True,
        ]
        if semester_id is not None:
            filters.append(UserRole.semester_id == semester_id)

        return await UserRole.find(*filters).to_list()

    async def list_active_by_user_and_unit(
        self,
        user_id: PydanticObjectId,
        unit_id: PydanticObjectId,
        semester_id: Optional[PydanticObjectId] = None,
    ) -> List[UserRole]:
        filters = [
            UserRole.user_id == user_id,
            UserRole.unit_id == unit_id,
            UserRole.is_active == True,
        ]
        if semester_id is not None:
            filters.append(UserRole.semester_id == semester_id)

        return await UserRole.find(*filters).to_list()

    async def get_active_by_user_role_unit_semester(
        self,
        user_id: PydanticObjectId,
        role_id: PydanticObjectId,
        unit_id: PydanticObjectId,
        semester_id: PydanticObjectId,
    ) -> UserRole | None:
        return await UserRole.find_one(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
            UserRole.unit_id == unit_id,
            UserRole.semester_id == semester_id,
            UserRole.is_active == True,
        )

    async def create(self, user_role: UserRole) -> UserRole:
        return await user_role.insert()

    async def deactivate(self, user_role: UserRole) -> UserRole:
        user_role.is_active = False
        return await user_role.save()
