from enum import Enum

from beanie import Document


class RoleCode(str, Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    STAFF = "STAFF"
    USER = "USER"


class Role(Document):
    code: RoleCode

    class Settings:
        name = "roles"
