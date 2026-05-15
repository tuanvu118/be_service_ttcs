from models.unit_event_submission_members import UnitEventSubmissionMember
from beanie import PydanticObjectId
from typing import Optional, List
from beanie.operators import In


class UnitEventSubmissionMembersRepo:
    async def create(self, unit_event_submission_member: UnitEventSubmissionMember) -> UnitEventSubmissionMember:
        return await unit_event_submission_member.insert()
    
    async def get_by_id(self, unit_event_submission_member_id: PydanticObjectId) -> Optional[UnitEventSubmissionMember]:
        return await UnitEventSubmissionMember.get(unit_event_submission_member_id)

    async def update_check_in(self, unit_event_submission_member_id: PydanticObjectId, check_in: bool) -> UnitEventSubmissionMember:
        unit_event_submission_member = await self.get_by_id(unit_event_submission_member_id)
        unit_event_submission_member.checkIn = check_in
        return await unit_event_submission_member.save()

    async def get_all_by_unit_event_submission_id(self, unit_event_submission_id: PydanticObjectId) -> List[UnitEventSubmissionMember]:
        return await UnitEventSubmissionMember.find(UnitEventSubmissionMember.unitEventSubmissionId == unit_event_submission_id).to_list()

    async def count_by_unit_event_submission_id(
        self, unit_event_submission_id: PydanticObjectId
    ) -> int:
        return await UnitEventSubmissionMember.find(
            UnitEventSubmissionMember.unitEventSubmissionId == unit_event_submission_id
        ).count()

    async def get_by_submission_and_user(
        self, unit_event_submission_id: PydanticObjectId, user_id: PydanticObjectId
    ) -> Optional[UnitEventSubmissionMember]:
        return await UnitEventSubmissionMember.find_one(
            UnitEventSubmissionMember.unitEventSubmissionId == unit_event_submission_id,
            UnitEventSubmissionMember.userId == user_id,
        )

    async def get_by_submission_and_student(
        self, unit_event_submission_id: PydanticObjectId, student_id: str
    ) -> Optional[UnitEventSubmissionMember]:
        return await UnitEventSubmissionMember.find_one(
            UnitEventSubmissionMember.unitEventSubmissionId == unit_event_submission_id,
            UnitEventSubmissionMember.studentId == student_id,
        )

    async def get_by_unit_event_and_user(
        self, unit_event_id: PydanticObjectId, user_id: PydanticObjectId
    ) -> Optional[UnitEventSubmissionMember]:
        return await UnitEventSubmissionMember.find_one(
            UnitEventSubmissionMember.unitEventId == unit_event_id,
            UnitEventSubmissionMember.userId == user_id,
        )

    async def get_by_unit_event_and_student(
        self, unit_event_id: PydanticObjectId, student_id: str
    ) -> Optional[UnitEventSubmissionMember]:
        return await UnitEventSubmissionMember.find_one(
            UnitEventSubmissionMember.unitEventId == unit_event_id,
            UnitEventSubmissionMember.studentId == student_id,
        )

    async def get_all_by_unit_event_submission_ids(
        self, unit_event_submission_ids: List[PydanticObjectId]
    ) -> List[UnitEventSubmissionMember]:
        if not unit_event_submission_ids:
            return []
        return await UnitEventSubmissionMember.find(
            In(UnitEventSubmissionMember.unitEventSubmissionId, unit_event_submission_ids)
        ).to_list()

    async def mark_checked_in_by_submission_ids_and_user(
        self,
        unit_event_submission_ids: List[PydanticObjectId],
        user_id: PydanticObjectId,
        student_id: str | None = None,
    ) -> int:
        if not unit_event_submission_ids:
            return 0

        members = await self.get_all_by_unit_event_submission_ids(unit_event_submission_ids)
        updated_count = 0
        normalized_student_id = str(student_id).strip() if student_id else None
        for member in members:
            matched_user = member.userId == user_id
            matched_student = (
                normalized_student_id is not None
                and member.studentId is not None
                and str(member.studentId).strip() == normalized_student_id
            )
            if not (matched_user or matched_student):
                continue
            if member.checkIn:
                continue
            member.checkIn = True
            await member.save()
            updated_count += 1
        return updated_count

    async def delete_all_by_unit_event_submission_id(
        self, unit_event_submission_id: PydanticObjectId
    ) -> None:
        members = await self.get_all_by_unit_event_submission_id(unit_event_submission_id)
        for member in members:
            await member.delete()
