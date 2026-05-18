from beanie import PydanticObjectId
from exceptions import ErrorCode, app_exception
from repositories.event_registration_repo import EventRegistrationRepository
from repositories.unit_event_submissions_repo import UnitEventSubmissionsRepo
from repositories.unit_event_submission_members_repo import UnitEventSubmissionMembersRepo
from repositories.user_repo import UserRepo
from schemas.attendance import ManualAttendanceRequest, ManualAttendanceResponse

class ManualAttendanceService:
    @staticmethod
    async def mark_manual_attendance(
        actor_id: PydanticObjectId,
        request: ManualAttendanceRequest,
    ) -> ManualAttendanceResponse:
        event_id = request.event_id
        user_id = request.user_id
        event_type = request.event_type

        # 1. Check if user is registered/member
        if event_type == "public":
            registration = await EventRegistrationRepository.get_by_event_and_user(event_id, user_id)
            if not registration:
                app_exception(
                    ErrorCode.USER_NOT_ALLOWED_FOR_EVENT, 
                    extra_detail="Người dùng chưa đăng ký tham gia sự kiện này"
                )
            
            # 2. Check if attendance already exists
            if registration.checked_in:
                app_exception(
                    ErrorCode.DUPLICATE_CHECKIN, 
                    extra_detail="Người dùng đã được điểm danh trước đó"
                )
                
            # 3. Mark as checked-in in registration record
            await EventRegistrationRepository.mark_checked_in(event_id, user_id)
            
        elif event_type == "unit":
            approved_submissions = await UnitEventSubmissionsRepo().get_all_approved_by_unit_event_id(event_id)
            submission_ids = [submission.id for submission in approved_submissions]
            if not submission_ids:
                app_exception(
                    ErrorCode.USER_NOT_ALLOWED_FOR_EVENT, 
                    extra_detail="Sự kiện không có đơn vị nào được duyệt tham gia"
                )
            
            members = await UnitEventSubmissionMembersRepo().get_all_by_unit_event_submission_ids(submission_ids)
            user = await UserRepo().get_by_id(user_id)
            student_id = str(user.student_id).strip() if user and user.student_id else None
            
            matched_members = []
            for member in members:
                matched_user = member.userId == user_id
                matched_student = (
                    student_id is not None
                    and member.studentId is not None
                    and str(member.studentId).strip() == student_id
                )
                if matched_user or matched_student:
                    matched_members.append(member)
            
            if not matched_members:
                app_exception(
                    ErrorCode.USER_NOT_ALLOWED_FOR_EVENT, 
                    extra_detail="Người dùng không thuộc danh sách tham gia sự kiện này"
                )
            
            # 2. Check if attendance already exists
            if any(member.checkIn for member in matched_members):
                app_exception(
                    ErrorCode.DUPLICATE_CHECKIN, 
                    extra_detail="Người dùng đã được điểm danh trước đó"
                )
                
            # 3. Mark as checked-in in member record
            matched_submission_ids = [member.unitEventSubmissionId for member in matched_members]
            await UnitEventSubmissionMembersRepo().mark_checked_in_by_submission_ids_and_user(
                matched_submission_ids,
                user_id,
                student_id=student_id,
            )
        else:
            app_exception(ErrorCode.INVALID_OPTION, extra_detail="event_type không hợp lệ")

        return ManualAttendanceResponse(
            event_id=event_id,
            user_id=user_id,
            event_type=event_type,
        )
