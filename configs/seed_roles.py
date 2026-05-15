import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from passlib.context import CryptContext
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from configs.database import get_db
from models.roles import Role, RoleCode
from models.semester import Semester
from models.unit import Unit
from models.users import User
from models.users_roles import UserRole


DEFAULT_ROLES = [RoleCode.ADMIN, RoleCode.MANAGER, RoleCode.STAFF, RoleCode.USER]


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

DEFAULT_SEMESTER_NAME = "Học kỳ 2"
LEGACY_DEFAULT_SEMESTER_NAMES = ("Hoc ky 2",)
DEFAULT_SEMESTER_ACADEMIC_YEAR = "2025-2026"
DEFAULT_SEMESTER_START = datetime(2026, 2, 1, tzinfo=timezone.utc)
DEFAULT_SEMESTER_END = datetime(2026, 8, 31, 23, 59, 59, tzinfo=timezone.utc)

SEED_LOCK_COLLECTION = "_startup_locks"
SEED_LOCK_NAME = "seed_roles"
SEED_LOCK_WAIT_SECONDS = 30
SEED_LOCK_LEASE_SECONDS = 120


async def _acquire_seed_lock() -> str:
    collection = get_db()[SEED_LOCK_COLLECTION]
    owner = str(uuid4())
    deadline = datetime.now(timezone.utc) + timedelta(seconds=SEED_LOCK_WAIT_SECONDS)

    while datetime.now(timezone.utc) < deadline:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=SEED_LOCK_LEASE_SECONDS)

        lock_doc = await collection.find_one_and_update(
            {
                "_id": SEED_LOCK_NAME,
                "$or": [
                    {"expires_at": {"$lte": now}},
                    {"owner": owner},
                ],
            },
            {
                "$set": {
                    "owner": owner,
                    "expires_at": expires_at,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if lock_doc and lock_doc.get("owner") == owner:
            return owner

        try:
            await collection.insert_one(
                {
                    "_id": SEED_LOCK_NAME,
                    "owner": owner,
                    "expires_at": expires_at,
                }
            )
            return owner
        except DuplicateKeyError:
            await asyncio.sleep(0.5)

    raise RuntimeError("Could not acquire startup seed lock")


async def _release_seed_lock(owner: str) -> None:
    collection = get_db()[SEED_LOCK_COLLECTION]
    await collection.delete_one({"_id": SEED_LOCK_NAME, "owner": owner})


async def _seed_roles_impl():
    for code in DEFAULT_ROLES:
        exists = await Role.find_one(Role.code == code)
        if not exists:
            await Role(code=code).insert()

    admin_user = await User.find_one(User.student_id == "ADMIN")
    if not admin_user:
        hashed_password = pwd_context.hash("ADMIN")

        admin_user = User(
            full_name="Administrator",
            email="admin@example.com",
            password_hash=hashed_password,
            student_id="ADMIN",
            class_name="ADMIN",
            avatar_url=None,
            date_of_birth=None,
        )
        admin_user = await admin_user.insert()

    has_any_unit = bool(await Unit.find_all().limit(1).to_list())
    default_unit = None
    if not has_any_unit:
        default_unit = await Unit.find_one(Unit.name == "DEFAULT")
        if not default_unit:
            default_unit = Unit(
                name="DEFAULT",
                logo=None,
                type="SYSTEM",
            )
            default_unit = await default_unit.insert()

    seeded_semester = await Semester.find_one(
        {
            "academic_year": DEFAULT_SEMESTER_ACADEMIC_YEAR,
            "name": {
                "$in": [DEFAULT_SEMESTER_NAME, *LEGACY_DEFAULT_SEMESTER_NAMES],
            },
        }
    )
    if not seeded_semester:
        seeded_semester = Semester(
            name=DEFAULT_SEMESTER_NAME,
            academic_year=DEFAULT_SEMESTER_ACADEMIC_YEAR,
            start_date=DEFAULT_SEMESTER_START,
            end_date=DEFAULT_SEMESTER_END,
            is_active=True,
        )
        seeded_semester = await seeded_semester.insert()
    else:
        seeded_semester.name = DEFAULT_SEMESTER_NAME
        seeded_semester.is_active = True
        seeded_semester.start_date = DEFAULT_SEMESTER_START
        seeded_semester.end_date = DEFAULT_SEMESTER_END
        await seeded_semester.save()

    other_active_semesters = await Semester.find(
        Semester.is_active == True,
        Semester.id != seeded_semester.id,
    ).to_list()
    for semester in other_active_semesters:
        semester.is_active = False
        await semester.save()

    admin_role = await Role.find_one(Role.code == RoleCode.ADMIN)
    if admin_role and default_unit:
        exists_user_role = await UserRole.find_one(
            (UserRole.user_id == admin_user.id),
            (UserRole.role_id == admin_role.id),
            (UserRole.unit_id == default_unit.id),
            (UserRole.semester_id == seeded_semester.id),
            (UserRole.is_active == True),
        )

        if not exists_user_role:
            await UserRole(
                user_id=admin_user.id,
                role_id=admin_role.id,
                unit_id=default_unit.id,
                semester_id=seeded_semester.id,
                is_active=True,
            ).insert()


async def seed_roles():
    lock_owner = await _acquire_seed_lock()
    try:
        await _seed_roles_impl()
    finally:
        await _release_seed_lock(lock_owner)
