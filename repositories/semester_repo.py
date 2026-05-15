from typing import List, Optional

from beanie import PydanticObjectId

from models.semester import Semester


class SemesterRepo:
    async def create(self, semester: Semester) -> Semester:
        return await semester.insert()

    async def get_by_id(self, semester_id: PydanticObjectId) -> Optional[Semester]:
        return await Semester.get(semester_id)

    async def list_all(self) -> List[Semester]:
        return await Semester.find_all().sort([("created_at", -1)]).to_list()

    async def get_active(self) -> Optional[Semester]:
        return await Semester.find_one(Semester.is_active == True)

    async def save(self, semester: Semester) -> Semester:
        return await semester.save()

    async def deactivate_active_except(
        self,
        semester_id: Optional[PydanticObjectId] = None,
    ) -> None:
        semesters = await Semester.find(Semester.is_active == True).to_list()
        for semester in semesters:
            if semester_id and semester.id == semester_id:
                continue
            semester.is_active = False
            await semester.save()
