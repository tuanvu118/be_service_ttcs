from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING

from configs.settings import DB_NAME, MONGO_URI


from models.event_registration import EventRegistration
from models.public_event import PublicEvent
from models.refresh_tokens import RefreshTokenSession
from models.report import Report
from models.roles import Role
from models.semester import Semester
from models.unit import Unit
from models.unit_event import UnitEvent
from models.unit_event_submission_members import UnitEventSubmissionMember
from models.unit_event_submissions import UnitEventSubmission
from models.user_unit import UserUnit
from models.users import User
from models.users_roles import UserRole
from models.event_promotion import EventPromotion

client = AsyncIOMotorClient(MONGO_URI)





async def init_db():
    await init_beanie(
        database=client[DB_NAME],
        document_models=[
            User,
            Role,
            UserRole,
            UserUnit,
            Unit,
            Semester,
            RefreshTokenSession,
            PublicEvent,
            Report,
            EventRegistration,
            UnitEvent,
            UnitEventSubmission,
            UnitEventSubmissionMember,
            EventPromotion,
        ],
    )


def get_db():
    return client[DB_NAME]
