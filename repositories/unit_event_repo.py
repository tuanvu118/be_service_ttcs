from models.unit_event import UnitEvent, UnitEventEnum
from datetime import datetime, timezone
from typing import List
from beanie import PydanticObjectId
from typing import Optional
from bson import Decimal128

def convert_bson_types(data):
    if isinstance(data, dict):
        return {k: convert_bson_types(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_bson_types(v) for v in data]
    elif isinstance(data, Decimal128):
        return data.to_decimal()
    return data

class UnitEventRepo:
    async def create(self, unit_event: UnitEvent) -> UnitEvent:
        return await unit_event.insert()
    
    async def get_all_active(self) -> List[UnitEvent]:
        return await UnitEvent.find(UnitEvent.deleted_at == None).to_list()


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

    async def list_active_by_semester_id_with_units(
        self,
        semester_id: Optional[PydanticObjectId] = None,
        skip: int = 0,
        limit: int = 10
    ) -> (List[dict], int):
        match_filter = {"deleted_at": None}
        if semester_id:
            match_filter["semesterId"] = semester_id

        total = await UnitEvent.find(match_filter).count()

        pipeline = [
            {"$match": match_filter},
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "units",
                    "localField": "listUnitId",
                    "foreignField": "_id",
                    "as": "assigned_units"
                }
            },
            {
                "$project": {
                    "id": "$_id",
                    "_id": 0,
                    "title": 1,
                    "description": 1,
                    "location": 1,
                    "point": 1,
                    "type": 1,
                    "event_start": 1,
                    "event_end": 1,
                    "registration_start": 1,
                    "registration_end": 1,
                    "is_student_registration": 1,
                    "limit_student_registration_in_one_unit": 1,
                    "semesterId": 1,
                    "created_at": 1,
                    "created_by": 1,
                    "assigned_units": {
                        "$map": {
                            "input": "$assigned_units",
                            "as": "unit",
                            "in": {
                                "id": "$$unit._id",
                                "name": "$$unit.name",
                                "logo": "$$unit.logo",
                                "type": "$$unit.type",
                                "cover_url": "$$unit.cover_url",
                                "introduction": "$$unit.introduction",
                                "established_year": "$$unit.established_year",
                                "email": "$$unit.email",
                                "fb_url": "$$unit.fb_url",
                                "member_count": "$$unit.member_count"
                            }
                        }
                    }
                }
            }
        ]

        raw_items = await UnitEvent.get_pymongo_collection().aggregate(pipeline).to_list(length=None)
        items = convert_bson_types(raw_items)
        return items, total

