from enum import Enum
from typing import Optional

from beanie import Document


class UnitType(str, Enum):
    LCK = "LCK"
    CLB = "CLB"
    SYSTEM = "SYSTEM"


class Unit(Document):
    name: Optional[str] = None
    logo: Optional[str] = None
    cover_url: Optional[str] = None
    introduction: Optional[str] = None
    type: Optional[UnitType] = UnitType.CLB
    established_year: Optional[int] = None
    email: Optional[str] = None
    fb_url: Optional[str] = None
    member_count: Optional[int] = 0

    class Settings:
        name = "units"
