from typing import List, Optional
from datetime import datetime, timedelta
from beanie import PydanticObjectId
from models.event_promotion import EventPromotion

class EventPromotionRepository:
    @staticmethod
    async def create(data: dict) -> EventPromotion:
        promotion = EventPromotion(**data)
        return await promotion.insert()

    @staticmethod
    async def get_by_id(id: PydanticObjectId) -> Optional[EventPromotion]:
        return await EventPromotion.get(id)

    @staticmethod
    async def get_all_for_admin(
        status: Optional[str] = None, 
        semester_id: Optional[PydanticObjectId] = None,
        skip: int = 0,
        limit: int = 10
    ):
        query = {}
        if status:
            query["status"] = status
        if semester_id:
            query["semester_id"] = semester_id
            
        cursor = EventPromotion.find(query)
        total = await cursor.count()
        items = await cursor.sort("-created_at").skip(skip).limit(limit).to_list()
        return items, total

    @staticmethod
    async def get_by_unit(
        unit_id: PydanticObjectId, 
        status: Optional[str] = None,
        semester_id: Optional[PydanticObjectId] = None,
        skip: int = 0,
        limit: int = 10
    ):
        query = {"unit_id": unit_id}
        if status:
            query["status"] = status
        if semester_id:
            query["semester_id"] = semester_id
            
        cursor = EventPromotion.find(query)
        total = await cursor.count()
        items = await cursor.sort("-created_at").skip(skip).limit(limit).to_list()
        return items, total

    @staticmethod
    async def get_active_for_students(
        now: datetime,
        skip: int = 0,
        limit: int = 10,
        unit_id: Optional[PydanticObjectId] = None
    ):
        # DA_DUYET and now < time.end + 3 days
        # In MongoDB: time.end >= now - 3 days
        threshold = now - timedelta(weeks=3)
        query = {
            "status": "DA_DUYET",
            "time.end": {"$gte": threshold}
        }
        if unit_id:
            query["unit_id"] = unit_id
        
        cursor = EventPromotion.find(query)
        total = await cursor.count()
        items = await cursor.sort("-time.start").skip(skip).limit(limit).to_list()
        return items, total

    @staticmethod
    async def update(promotion: EventPromotion) -> EventPromotion:
        return await promotion.save()

    @staticmethod
    async def delete(promotion: EventPromotion):
        await promotion.delete()
