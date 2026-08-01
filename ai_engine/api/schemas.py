from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ContractPreference = Literal[
    "monthly_rent",
    "jeonse",
    "both",
]

HousingType = Literal[
    "apartment",
    "officetel",
    "row_house",
    "single_multi_house",
]

MinimumAreaBucket = Literal[
    "any",
    "under_20",
    "20_30",
    "30_40",
    "over_40",
]

LoanPreference = Literal[
    "available",
    "minimize",
    "no_loan",
]

MatchStatus = Literal[
    "likely_eligible",
    "needs_more_info",
    "ineligible",
]

JudgementCode = Literal[
    "recommended",
    "conditionally_recommended",
    "consider_other_area",
    "budget_exceeded",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )


# =========================================================
# 요청 모델
# =========================================================

class UserProfileRequest(StrictModel):
    birth_date: date

    evaluation_date: date | None = None

    monthly_take_home_income_manwon: float = Field(
        ge=0,
        description="월 실수령 소득, 만원 단위",
    )

    household_annual_income_manwon: float | None = Field(
        default=None,
        ge=0,
        description="본인·배우자 합산 연소득, 만원 단위",
    )

    monthly_living_expense_manwon: float = Field(
        ge=0,
        description="월 비주거 생활비, 만원 단위",
    )

    monthly_debt_payment_manwon: float = Field(
        default=0,
        ge=0,
        description="기존 월 부채 상환액, 만원 단위",
    )

    target_monthly_savings_manwon: float = Field(
        default=0,
        ge=0,
        description="월 목표 저축액, 만원 단위",
    )

    housing_funds_manwon: float = Field(
        ge=0,
        description="주거 마련에 사용할 수 있는 총자금",
    )

    is_no_home: bool | None = None

    all_household_members_no_home: bool | None = None

    household_head_status: Literal[
        "household_head",
        "prospective_household_head",
        "household_member",
    ] | None = None

    is_single_household_head: bool | None = None

    passes_fund_asset_test: bool | None = None


class HousingPreferenceRequest(StrictModel):
    contract_preference: ContractPreference

    preferred_housing_types: list[
        HousingType
    ] = Field(
        min_length=1,
    )

    minimum_area_bucket: MinimumAreaBucket = "any"

    loan_preference: LoanPreference = "minimize"

    allowed_district_names: list[str] | None = None


class CostAssumptionRequest(StrictModel):
    affordable_monthly_housing_cost_manwon: float | None = Field(
        default=None,
        ge=0,
        description=(
            "하위 호환을 위해 유지되는 입력값입니다. "
            "추천 엔진은 이 값을 직접 사용하지 않고 "
            "사용자 재무 입력을 기반으로 적정 주거비를 "
            "서버에서 다시 계산합니다."
        ),
    )

    moving_initial_cost_manwon: float = Field(
        default=100,
        ge=0,
        description="이사비·중개보수 등 초기비용",
    )

    minimum_cash_reserve_manwon: float = Field(
        default=300,
        ge=0,
        description="이사 후 남길 최소 비상예비금",
    )

    management_fee_assumption_manwon: float = Field(
        default=8,
        ge=0,
        description="월 관리비 가정값",
    )

    utilities_assumption_manwon: float = Field(
        default=7,
        ge=0,
        description="월 공과금 가정값",
    )


class HousingRecommendationRequest(StrictModel):
    request_id: str | None = None

    user_profile: UserProfileRequest

    housing_preference: HousingPreferenceRequest

    cost_assumptions: CostAssumptionRequest = Field(
        default_factory=CostAssumptionRequest,
    )

    top_n: int = Field(
        default=5,
        ge=1,
        le=10,
    )


# =========================================================
# 응답 모델
# =========================================================

class AffordableBudgetResponse(StrictModel):
    amount_manwon: float
    source: str


class MarketPriceResponse(StrictModel):
    deposit_q25_manwon: float | None
    deposit_median_manwon: float
    deposit_q75_manwon: float | None

    monthly_rent_q25_manwon: float | None
    monthly_rent_median_manwon: float
    monthly_rent_q75_manwon: float | None

    contract_count: int
    confidence: str
    contract_scope: str | None
    data_start_date: str | None
    data_end_date: str | None


class InitialFundsResponse(StrictModel):
    total_housing_funds_manwon: float
    deposit_allocable_cash_manwon: float

    moving_initial_cost_manwon: float
    minimum_cash_reserve_manwon: float

    deposit_gap_before_loan_manwon: float
    estimated_loan_manwon: float
    remaining_gap_after_loan_manwon: float

    own_cash_required_for_deposit_manwon: float
    liquid_cash_after_move_manwon: float
    upfront_cash_shortfall_manwon: float
    reserve_shortfall_manwon: float


class MonthlyCostResponse(StrictModel):
    monthly_rent_manwon: float
    management_fee_manwon: float
    utilities_manwon: float
    loan_interest_manwon: float

    total_monthly_housing_cost_manwon: float
    affordable_monthly_housing_cost_manwon: float
    affordability_ratio: float


class FinanceSummaryResponse(StrictModel):
    applied: bool

    product_id: str | None
    product_name: str | None

    match_status: MatchStatus | None
    decision_confidence: str

    estimated_loan_manwon: float
    estimated_monthly_interest_manwon: float
    remaining_gap_manwon: float

    missing_fields: list[str]

    official_url: str | None

    disclaimer: str


class StressTestResponse(StrictModel):
    interest_rate_increase_pct_point: float
    additional_monthly_interest_manwon: float
    stressed_total_monthly_cost_manwon: float


class FutureSimulationResponse(StrictModel):
    available: bool

    scenario_feasible_at_move_in: bool | None = None

    monthly_saving_capacity_manwon: float | None = None

    target_monthly_savings_manwon: float | None = None

    can_maintain_target_savings: bool | None = None

    liquid_cash_after_move_manwon: float | None = None

    projected_liquid_assets_after_12_months_manwon: (
        float | None
    ) = None

    projected_net_assets_after_12_months_manwon: (
        float | None
    ) = None

    calculation_note: str | None = None

    reason: str | None = None


class JudgementResponse(StrictModel):
    code: JudgementCode
    label: str


class RecommendationCardResponse(StrictModel):
    rank: int

    candidate_id: str

    title: str

    transaction_type: Literal[
        "monthly_rent",
        "jeonse",
    ]

    transaction_type_label: str

    district_code: str
    district_name: str

    housing_type: HousingType
    housing_type_label: str

    area_label: str

    deposit_bucket_label: str | None

    score_total: float
    score_breakdown: dict[str, float]

    judgement: JudgementResponse

    market_price: MarketPriceResponse
    initial_funds: InitialFundsResponse
    monthly_cost: MonthlyCostResponse
    finance: FinanceSummaryResponse
    stress_test: StressTestResponse
    future_simulation: FutureSimulationResponse

    explanations: dict[str, str]


class HousingRecommendationResponse(StrictModel):
    request_id: str

    generated_at: datetime

    engine_version: str

    recommendation_basis: str

    affordable_budget: AffordableBudgetResponse

    candidate_counts_before_full_scoring: dict[
        str,
        int,
    ]

    recommendation_count: int

    recommendations: list[
        RecommendationCardResponse
    ]

    limitations: list[str]


class HealthResponse(StrictModel):
    status: Literal["ok"]

    service: str

    engine_version: str
