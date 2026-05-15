from typing import Optional, List

from beanie import PydanticObjectId

from models.roles import Role


class RoleRepo:
    async def get_by_id(self, role_id: PydanticObjectId) -> Optional[Role]:
        return await Role.get(role_id)

    async def get_by_code(self, code: str) -> Optional[Role]:
        return await Role.find_one(Role.code == code)

    async def list_all(self) -> List[Role]:
        return await Role.find_all().to_list()

