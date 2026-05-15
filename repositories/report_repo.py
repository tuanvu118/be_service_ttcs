from typing import Tuple
from typing import List, Optional, Any
from beanie import PydanticObjectId

from models.report import Report
from models.public_event import PublicEvent


class ReportRepository:

    @staticmethod
    async def create(data: dict) -> Report:
        report = Report(**data)
        await report.insert()
        return report

    @staticmethod
    async def get_by_id(report_id: PydanticObjectId) -> Optional[Report]:
        return await Report.get(report_id)

    @staticmethod
    async def get_by_unique(
        unit_id: PydanticObjectId,
        month: int,
        year: int
    ) -> Optional[Report]:
        return await Report.find_one({
            "unit_id": unit_id,
            "month": month,
            "year": year,
        })

    @staticmethod
    async def get_all() -> List[Report]:
        return await Report.find_all().to_list()

    @staticmethod
    async def get_by_unit(
        unit_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 10
    ) -> (Tuple[List[Report], int]):
        cursor = Report.find({
            "unit_id": unit_id
        })
        total = await cursor.count()
        items = await cursor.sort("-updated_at").skip(skip).limit(limit).to_list()
        return items, total

    @staticmethod
    async def save(report: Report) -> Report:
        await report.save()
        return report

    @staticmethod
    async def delete(report: Report):
        await report.delete()

    @staticmethod
    async def get_filtered(
        month: Optional[int] = None,
        year: Optional[int] = None,
        unit_id: Optional[PydanticObjectId] = None,
        status: Optional[Any] = None,
        skip: int = 0,
        limit: int = 10
    ) -> (Tuple[List[Report], int]):
        query = {}
        if month is not None:
            query["month"] = month
        if year is not None:
            query["year"] = year
        if unit_id is not None:
            query["unit_id"] = unit_id
        if status is not None:
            query["status"] = status
        
        cursor = Report.find(query)
        total = await cursor.count()
        items = await cursor.sort("-updated_at").skip(skip).limit(limit).to_list()
        return items, total

    @staticmethod
    async def get_by_month_year(
        month: int,
        year: int
    ) -> List[Report]:
        return await ReportRepository.get_filtered(month=month, year=year)

    @staticmethod
    async def get_stats(
        month: Optional[int] = None,
        year: Optional[int] = None,
        unit_id: Optional[PydanticObjectId] = None,
    ) -> dict:
        query = {}
        if month is not None:
            query["month"] = month
        if year is not None:
            query["year"] = year
        if unit_id is not None:
            query["unit_id"] = unit_id
            
        pending = await Report.find(query, {"status": "CHO_DUYET"}).count()
        approved = await Report.find(query, {"status": "DA_DUYET"}).count()
        rejected = await Report.find(query, {"status": {"$in": ["YEU_CAU_NOP_LAI", "BI_TU_CHOI"]}}).count()
        
        return {
            "pending": pending,
            "approved": approved,
            "rejected": rejected
        }

    @staticmethod
    async def get_public_events_by_ids(
        ids: List[PydanticObjectId]
    ) -> List[PublicEvent]:

        if not ids:
            return []

        return await PublicEvent.find(
            {"_id": {"$in": ids}}
        ).to_list()