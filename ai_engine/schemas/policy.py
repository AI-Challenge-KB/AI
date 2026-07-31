from typing import Literal, Optional

from pydantic import BaseModel, Field


EligibilityStatus = Literal[
    "eligible",
    "ineligible",
    "needs_review",
]


class HousingPolicy(BaseModel):
    policy_id: str
    policy_name: str
    provider: str
    support_type: str
    target_region_code: Optional[str] = None

    age_min: Optional[int] = None
    age_max: Optional[int] = None

    income_limit: Optional[int] = Field(default=None, ge=0)
    asset_limit: Optional[int] = Field(default=None, ge=0)

    homeless_required: bool = False
    employment_condition: Optional[str] = None

    monthly_support_amount: int = Field(default=0, ge=0)
    total_support_amount: int = Field(default=0, ge=0)

    application_start: Optional[str] = None
    application_end: Optional[str] = None

    official_source: str
    checked_at: str
    notes: Optional[str] = None