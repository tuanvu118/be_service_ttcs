from datetime import datetime
from typing import List, Optional

from beanie import PydanticObjectId

from models.public_event import PublicEvent


class PublicEventRepository:

    @staticmethod
    async def create(data: dict) -> PublicEvent:
        event = PublicEvent(**data)
        await event.insert()
        return event

    @staticmethod
    async def get_by_id(event_id: PydanticObjectId):
        return await PublicEvent.get(event_id)

    @staticmethod
    async def get_all(
        semester_id: Optional[PydanticObjectId] = None,
        skip: int = 0,
        limit: int = 10
    ):
        query = {}
        if semester_id:
            query["semester_id"] = semester_id
            
        cursor = PublicEvent.find(query)
        total = await cursor.count()
        items = await cursor.sort("-created_at").skip(skip).limit(limit).to_list()
        return items, total

    @staticmethod
    async def update(event_id: PydanticObjectId, data: dict):
        event = await PublicEvent.get(event_id)
        if not event:
            return None

        await event.update({"$set": data})

        return await PublicEvent.get(event_id)

    @staticmethod
    async def get_by_ids(
            ids: List[PydanticObjectId]
    ) -> List[PublicEvent]:

        if not ids:
            return []

        return await PublicEvent.find(
            {"_id": {"$in": ids}}
        ).to_list()

    @staticmethod
    async def get_valid_events(
        now: datetime, 
        semester_id: Optional[PydanticObjectId] = None,
        search: Optional[str] = None,
        started_after: Optional[datetime] = None,
        started_before: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 10
    ):
        query = {
            "event_end": {"$gte": now}
        }

        if semester_id:
            query["semester_id"] = semester_id
            
        if search:
            query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}}
            ]
            
        if started_after or started_before:
            time_query = {}
            if started_after:
                time_query["$gte"] = started_after
            if started_before:
                time_query["$lte"] = started_before
            query["event_start"] = time_query
            
        cursor = PublicEvent.find(query)
        total = await cursor.count()
        items = await cursor.sort("event_start").skip(skip).limit(limit).to_list()
        return items, total

    @staticmethod
    async def delete(event_id: PydanticObjectId):
        event = await PublicEvent.get(event_id)
        if event:
            await event.delete()
            return True
        return False
