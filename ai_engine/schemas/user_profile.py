from typing import Literal, Optional

from pydantic import BaseModel, Field


EmploymentStatus = Literal[
    "student",
    "job_seeker",
    "employee",
    "self_employed",
    "freelancer",
    "other",
]

HousingType = Literal[
    "monthly_rent",
    "jeonse",
    "public_rental",
    "undecided",
]


class UserProfile(BaseModel):
    """청년 주거 금융 추천에 사용되는 사용자 금융 프로필."""

    user_id: str
    age: int = Field(ge=19, le=100)

    employment_status: EmploymentStatus
    household_type: str = "single"
    marital_status: str = "single"
    is_homeless: bool = True

    current_region: str
    desired_region: str
    workplace_region: Optional[str] = None

    monthly_income: int = Field(ge=0)
    additional_income: int = Field(default=0, ge=0)

    # 현재 주거비를 제외한 필수 생활비
    non_housing_living_expenses: int = Field(ge=0)

    current_assets: int = Field(default=0, ge=0)
    available_deposit: int = Field(default=0, ge=0)

    current_debt: int = Field(default=0, ge=0)
    monthly_debt_payment: int = Field(default=0, ge=0)

    # 사용자가 원하는 월 저축 목표
    target_monthly_savings: int = Field(default=0, ge=0)

    # 사용자가 원하는 월 비상자금 적립액
    target_emergency_fund_contribution: int = Field(
        default=0,
        ge=0,
    )

    preferred_housing_type: HousingType = "undecided"

    @property
    def total_monthly_income(self) -> int:
        return self.monthly_income + self.additional_income


class BudgetPreference(BaseModel):
    """사용자가 선택한 주거비 계산 기준."""

    # 목표 저축액 중 실제로 유지하려는 비율
    savings_preservation_ratio: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )

    # 비상자금 적립액 중 실제로 유지하려는 비율
    emergency_fund_preservation_ratio: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )