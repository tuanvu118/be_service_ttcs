from models.unit_event_submissions import (
    UnitEventSubmission,
    UnitEventSubmissionStatus,
)
from beanie import PydanticObjectId
from datetime import datetime
from typing import Optional, List

class UnitEventSubmissionsRepo:
    async def create(self, unit_event_submission: UnitEventSubmission) -> UnitEventSubmission:
        return await unit_event_submission.insert()
    
    async def get_by_id(self, unit_event_submission_id: PydanticObjectId) -> Optional[UnitEventSubmission]:
        return await UnitEventSubmission.get(unit_event_submission_id)
    
    async def get_all(self) -> List[UnitEventSubmission]:
        return await UnitEventSubmission.find_all().to_list()
    
    async def update(self, unit_event_submission: UnitEventSubmission) -> UnitEventSubmission:
        return await unit_event_submission.save()
    
    async def delete(self, unit_event_submission: UnitEventSubmission) -> None:
        await unit_event_submission.delete()

    async def get_by_unit_event_id_and_unit_id(self, unit_event_id: PydanticObjectId, unit_id: PydanticObjectId) -> Optional[UnitEventSubmission]:
        return await UnitEventSubmission.find_one(
            UnitEventSubmission.unitEventId == unit_event_id,
            UnitEventSubmission.unitId == unit_id
        )

    async def get_all_by_unit_event_id(
        self, unit_event_id: PydanticObjectId
    ) -> List[UnitEventSubmission]:
        return await UnitEventSubmission.find(
            UnitEventSubmission.unitEventId == unit_event_id
        ).to_list()

    async def get_all_approved_by_unit_event_id(
        self, unit_event_id: PydanticObjectId
    ) -> List[UnitEventSubmission]:
        return await UnitEventSubmission.find(
            UnitEventSubmission.unitEventId == unit_event_id,
            UnitEventSubmission.status == UnitEventSubmissionStatus.APPROVED,
        ).to_list()

    async def get_approved_by_unit_and_date_range(
        self, 
        unit_id: PydanticObjectId,
        start_date: datetime,
        end_date: datetime
    ) -> List[UnitEventSubmission]:
        return await UnitEventSubmission.find(
            UnitEventSubmission.unitId == unit_id,
            UnitEventSubmission.status == UnitEventSubmissionStatus.APPROVED,
            UnitEventSubmission.submittedAt >= start_date,
            UnitEventSubmission.submittedAt <= end_date
        ).to_list()
