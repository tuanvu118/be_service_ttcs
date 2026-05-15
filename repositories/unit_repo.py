from typing import List, Optional

from beanie import PydanticObjectId
from beanie.operators import In

from models.unit import Unit


class UnitRepo:
    async def create(self, unit: Unit) -> Unit:
        return await unit.insert()

    async def get_by_id(self, unit_id: PydanticObjectId) -> Optional[Unit]:
        return await Unit.get(unit_id)

    async def get_by_name(self, name: str) -> Optional[Unit]:
        return await Unit.find_one(Unit.name == name)

    async def list_all(self) -> List[Unit]:
        return await Unit.find_all().to_list()

    async def list_by_ids(self, unit_ids: List[PydanticObjectId]) -> List[Unit]:
        if not unit_ids:
            return []
        return await Unit.find(In(Unit.id, unit_ids)).to_list()

    async def delete(self, unit: Unit) -> None:
        await unit.delete()

    async def update(self, unit: Unit) -> Unit:
        return await unit.save()
