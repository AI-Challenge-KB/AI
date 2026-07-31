from typing import Literal, Optional

from pydantic import BaseModel, Field



HousingPlanType = Literal[
    "monthly_rent",
    "jeonse",
    "public_rental",
    "purchase",
]


class HousingPlan(BaseModel):
    """비교 대상이 되는 하나의 주거 플랜."""

    plan_id: str
    plan_name: str
    plan_type: HousingPlanType

    region_code: str
    region_name: str

    deposit: int = Field(default=0, ge=0)
    monthly_rent: int = Field(default=0, ge=0)
    management_fee: int = Field(default=0, ge=0)
    utilities: int = Field(default=0, ge=0)

    loan_amount: int = Field(default=0, ge=0)
    annual_interest_rate: float = Field(default=0.0, ge=0.0)

    monthly_policy_support: int = Field(default=0, ge=0)
    monthly_interest_support: int = Field(default=0, ge=0)

    commute_cost_change: int = 0
    commute_minutes: Optional[int] = Field(default=None, ge=0)

    contract_safety_score: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
    )