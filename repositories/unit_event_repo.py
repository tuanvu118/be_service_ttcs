from models.unit_event import UnitEvent, UnitEventEnum
from datetime import datetime, timezone
from typing import List
from beanie import PydanticObjectId
from typing import Optional

class UnitEventRepo:
    async def create(self, unit_event: UnitEvent) -> UnitEvent:
        return await unit_event.insert()
    
    async def get_all_active(self) -> List[UnitEvent]:
        return await UnitEvent.find(UnitEvent.deleted_at == None).to_list()

    async def list_active_by_semester_id(
        self, 
        semester_id: Optional[PydanticObjectId] = None,
        skip: int = 0,
        limit: int = 10
    ) -> (List[UnitEvent], int):
        query = {
            "deleted_at": None
        }
        if semester_id and semester_id != 'all':
            query["semesterId"] = semester_id
            
        cursor = UnitEvent.find(query)
        total = await cursor.count()
        items = await cursor.sort("-created_at").skip(skip).limit(limit).to_list()
        return items, total

    async def list_by_unit_id(self, unit_id: PydanticObjectId) -> List[UnitEvent]:
        """Lấy danh sách unit_events có unit_id trong listUnitId."""
        return await UnitEvent.find(
            UnitEvent.deleted_at == None,
            UnitEvent.listUnitId == unit_id,
        ).to_list()

    async def list_by_unit_id_and_semester_id(
        self, unit_id: PydanticObjectId, semester_id: PydanticObjectId
    ) -> List[UnitEvent]:
        return await UnitEvent.find(
            UnitEvent.deleted_at == None,
            UnitEvent.listUnitId == unit_id,
            UnitEvent.semesterId == semester_id,
        ).to_list()

    async def get_all(self) -> List[UnitEvent]:
        return await UnitEvent.find_all().to_list()

    async def list_expired_htsk_events_by_registration_end(
        self,
        now: datetime | None = None,
    ) -> List[UnitEvent]:
        deadline = now or datetime.now(timezone.utc)
        return await UnitEvent.find(
            UnitEvent.deleted_at == None,
            UnitEvent.type == UnitEventEnum.HTSK,
            UnitEvent.registration_end != None,
            UnitEvent.registration_end <= deadline,
        ).to_list()
    
    async def get_by_id(self, unit_event_id: PydanticObjectId) -> Optional[UnitEvent]:
        return await UnitEvent.find_one(
            UnitEvent.id == unit_event_id, UnitEvent.deleted_at == None
        )

    async def update(self, unit_event: UnitEvent) -> UnitEvent:
        return await unit_event.save()
    
    async def delete(self, unit_event: UnitEvent) -> None:
        await unit_event.delete()

    @staticmethod
    async def get_by_ids(
            event_ids: List[PydanticObjectId],
    ):
        return await UnitEvent.find(
            {"_id": {"$in": event_ids}}
        ).to_list()

