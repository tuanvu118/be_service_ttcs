from datetime import datetime
from typing import List, Optional

from beanie import PydanticObjectId
from bson import Decimal128

from models.public_event import PublicEvent

def convert_bson_types(data):
    if isinstance(data, dict):
        return {k: convert_bson_types(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_bson_types(v) for v in data]
    elif isinstance(data, Decimal128):
        return data.to_decimal()
    return data

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
    async def get_all_with_participants(
        match_filter: dict,
        skip: int = 0,
        limit: int = 10
    ) -> (List[dict], int):
        total = await PublicEvent.find(match_filter).count()
        
        pipeline = [
            {"$match": match_filter},
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "event_registrations",
                    "let": {"event_id": "$_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$event_id", "$$event_id"]},
                                        {"$eq": ["$event_type", "public"]}
                                    ]
                                }
                            }
                        },
                        {"$count": "count"}
                    ],
                    "as": "registration_counts"
                }
            },
            {
                "$project": {
                    "id": "$_id",
                    "_id": 0,
                    "title": 1,
                    "description": 1,
                    "image_url": 1,
                    "point": 1,
                    "location": 1,
                    "max_participants": 1,
                    "registration_start": 1,
                    "registration_end": 1,
                    "event_start": 1,
                    "event_end": 1,
                    "semester_id": 1,
                    "form_fields": 1,
                    "created_at": 1,
                    "current_participants": {
                        "$ifNull": [
                            {"$arrayElemAt": ["$registration_counts.count", 0]},
                            0
                        ]
                    }
                }
            }
        ]
        
        raw_items = await PublicEvent.get_pymongo_collection().aggregate(pipeline).to_list(length=None)
        items = convert_bson_types(raw_items)
        return items, total

    @staticmethod
    async def get_valid_with_participants(
        match_filter: dict,
        skip: int = 0,
        limit: int = 10
    ) -> (List[dict], int):
        total = await PublicEvent.find(match_filter).count()
        
        pipeline = [
            {"$match": match_filter},
            {"$sort": {"event_start": 1}},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "event_registrations",
                    "let": {"event_id": "$_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$event_id", "$$event_id"]},
                                        {"$eq": ["$event_type", "public"]}
                                    ]
                                }
                            }
                        },
                        {"$count": "count"}
                    ],
                    "as": "registration_counts"
                }
            },
            {
                "$project": {
                    "id": "$_id",
                    "_id": 0,
                    "title": 1,
                    "description": 1,
                    "image_url": 1,
                    "point": 1,
                    "location": 1,
                    "max_participants": 1,
                    "registration_start": 1,
                    "registration_end": 1,
                    "event_start": 1,
                    "event_end": 1,
                    "semester_id": 1,
                    "form_fields": 1,
                    "created_at": 1,
                    "current_participants": {
                        "$ifNull": [
                            {"$arrayElemAt": ["$registration_counts.count", 0]},
                            0
                        ]
                    }
                }
            }
        ]
        
        raw_items = await PublicEvent.get_pymongo_collection().aggregate(pipeline).to_list(length=None)
        items = convert_bson_types(raw_items)
        return items, total

    @staticmethod
    async def delete(event_id: PydanticObjectId):
        event = await PublicEvent.get(event_id)
        if event:
            await event.delete()
            return True
        return False
