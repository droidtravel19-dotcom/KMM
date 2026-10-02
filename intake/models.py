from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class PracticeArea(str, Enum):
    LAND = "Land & Conveyancing"
    SUCCESSION = "Succession & Probate"
    LITIGATION = "Civil Litigation"
    COMMERCIAL = "Commercial & Corporate"
    FAMILY = "Family & Children"
    EMPLOYMENT = "Employment & Labour"
    CRIMINAL = "Criminal"
    OTHER = "Other / Unclear"


class Urgency(str, Enum):
    HIGH = "high"      # hard deadline, arrest/detention, eviction, court date within days
    NORMAL = "normal"
    LOW = "low"


class EnquiryIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    phone: str = Field(default="", max_length=50)
    subject: str = Field(default="", max_length=300)
    message: str = Field(min_length=1, max_length=20000)
    source: str = "web"


class Triage(BaseModel):
    practice_area: PracticeArea
    urgency: Urgency = Urgency.NORMAL
    summary: str
    key_facts: list[str] = []
    missing_info: list[str] = []
    opposing_parties: list[str] = []  # names mentioned, for the conflict check
    method: str = "ai"  # "ai" or "keyword"
