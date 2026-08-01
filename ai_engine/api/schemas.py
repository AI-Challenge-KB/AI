from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


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
    """
    API 요청/응답에서 정의되지 않은 필드를 허용하지 않는다.
    """

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
        description=(
            "월 실수령 소득, 만원 단위"
        ),
    )

    household_annual_income_manwon: (
        float | None
    ) = Field(
        default=None,
        ge=0,
        description=(
            "본인·배우자 합산 연소득, 만원 단위. "
            "월 실수령 소득에서 자동 환산하지 않으며, "
            "입력하지 않은 경우 금융상품 소득 요건은 "
            "추가 확인이 필요한 상태로 판단할 수 있습니다."
        ),
    )

    monthly_living_expense_manwon: float = Field(
        ge=0,
        description=(
            "현재 주거비를 제외한 "
            "월 비주거 필수 생활비, 만원 단위"
        ),
    )

    monthly_debt_payment_manwon: float = Field(
        default=0,
        ge=0,
        description=(
            "기존 월 부채 상환액, 만원 단위"
        ),
    )

    target_monthly_savings_manwon: float = Field(
        default=0,
        ge=0,
        description=(
            "월 목표 저축액, 만원 단위"
        ),
    )

    housing_funds_manwon: float = Field(
        ge=0,
        description=(
            "보증금, 이사 초기비용, 비상예비금 등에 "
            "사용할 수 있는 총 주거자금, 만원 단위"
        ),
    )

    is_no_home: bool | None = None

    all_household_members_no_home: (
        bool | None
    ) = None

    household_head_status: Literal[
        "household_head",
        "prospective_household_head",
        "household_member",
    ] | None = None

    is_single_household_head: (
        bool | None
    ) = None

    passes_fund_asset_test: (
        bool | None
    ) = None


class HousingPreferenceRequest(StrictModel):
    contract_preference: (
        ContractPreference
    )

    preferred_housing_types: list[
        HousingType
    ] = Field(
        min_length=1,
        description=(
            "선호 주택 유형 목록"
        ),
    )

    minimum_area_bucket: (
        MinimumAreaBucket
    ) = "any"

    loan_preference: LoanPreference = (
        "minimize"
    )

    preferred_district_names: (
        list[str] | None
    ) = Field(
        default=None,
        max_length=2,
        description=(
            "선호 지역을 우선순위 순서로 입력합니다. "
            "첫 번째 지역은 1순위, 두 번째 지역은 "
            "2순위입니다. "
            "서울 자치구 기준 최대 2개까지 "
            "입력할 수 있습니다. "
            "추천 후보를 제거하는 조건이 아니라 "
            "추천 점수에 반영되는 soft preference입니다."
        ),
    )

    allowed_district_names: (
        list[str] | None
    ) = Field(
        default=None,
        description=(
            "추천을 허용할 서울 자치구 목록입니다. "
            "값이 지정되면 목록에 포함되지 않은 지역은 "
            "추천 후보에서 제외되는 hard filter입니다."
        ),
    )


class CostAssumptionRequest(StrictModel):
    affordable_monthly_housing_cost_manwon: (
        float | None
    ) = Field(
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
        description=(
            "이사비·중개보수 등 초기비용, "
            "만원 단위"
        ),
    )

    minimum_cash_reserve_manwon: (
        float
    ) = Field(
        default=300,
        ge=0,
        description=(
            "이사 후 남길 최소 비상예비금, "
            "만원 단위"
        ),
    )

    management_fee_assumption_manwon: (
        float
    ) = Field(
        default=8,
        ge=0,
        description=(
            "월 관리비 가정값, 만원 단위"
        ),
    )

    utilities_assumption_manwon: float = (
        Field(
            default=7,
            ge=0,
            description=(
                "월 공과금 가정값, 만원 단위"
            ),
        )
    )


class HousingRecommendationRequest(
    StrictModel
):
    request_id: str | None = None

    user_profile: UserProfileRequest

    housing_preference: (
        HousingPreferenceRequest
    )

    cost_assumptions: (
        CostAssumptionRequest
    ) = Field(
        default_factory=(
            CostAssumptionRequest
        ),
    )

    top_n: int = Field(
        default=5,
        ge=1,
        le=10,
    )


# =========================================================
# 응답 모델
# =========================================================

class AffordableBudgetResponse(
    StrictModel
):
    amount_manwon: float

    source: str


class MarketPriceResponse(StrictModel):
    deposit_q25_manwon: (
        float | None
    )

    deposit_median_manwon: float

    deposit_q75_manwon: (
        float | None
    )

    monthly_rent_q25_manwon: (
        float | None
    )

    monthly_rent_median_manwon: float

    monthly_rent_q75_manwon: (
        float | None
    )

    contract_count: int

    confidence: str

    contract_scope: str | None

    data_start_date: str | None

    data_end_date: str | None


class InitialFundsResponse(StrictModel):
    total_housing_funds_manwon: float

    deposit_allocable_cash_manwon: (
        float
    )

    moving_initial_cost_manwon: float

    minimum_cash_reserve_manwon: float

    deposit_gap_before_loan_manwon: (
        float
    )

    estimated_loan_manwon: float

    remaining_gap_after_loan_manwon: (
        float
    )

    own_cash_required_for_deposit_manwon: (
        float
    )

    liquid_cash_after_move_manwon: float

    upfront_cash_shortfall_manwon: (
        float
    )

    reserve_shortfall_manwon: float


class MonthlyCostResponse(StrictModel):
    monthly_rent_manwon: float

    management_fee_manwon: float

    utilities_manwon: float

    loan_interest_manwon: float

    # 실제 자기자금으로 투입되는 보증금
    own_cash_deposit_manwon: (
        float | None
    ) = None

    # 자기자금 보증금의 월 환산 기회비용
    deposit_opportunity_cost_manwon: (
        float | None
    ) = None

    # 현재 거주지 대비 통근비 증감
    commute_cost_change_manwon: (
        float | None
    ) = None

    # 월세지원·이자지원 등의 월 환산 지원액
    monthly_support_manwon: (
        float | None
    ) = None

    # 정책지원 차감 전 월 환산 주거비
    gross_monthly_housing_cost_manwon: (
        float | None
    ) = None

    # 정책지원 등을 반영한 최종 월 주거비
    total_monthly_housing_cost_manwon: (
        float
    )

    affordable_monthly_housing_cost_manwon: (
        float
    )

    affordability_ratio: float

class PolicySupportResponse(
    StrictModel
):
    support_id: str

    support_code: str

    support_name: str

    support_type: str

    match_status: MatchStatus

    application_status: str

    currently_applicable: bool

    affects_deposit_gap: bool

    used_in_cost_scenario: bool

    potential_monthly_support_manwon: (
        float
    )

    applied_monthly_support_manwon: (
        float
    )

    missing_fields: list[str]

    reason_codes: list[str]

class FinanceSummaryResponse(StrictModel):
    applied: bool

    product_id: str | None
    product_name: str | None

    match_status: MatchStatus | None
    decision_confidence: str

    estimated_loan_manwon: float
    estimated_monthly_interest_manwon: float
    remaining_gap_manwon: float

    # available 모드에서,
    # 실제 비용 계산에는 적용하지 않았지만
    # 이용 가능한 월세 금융상품이 있을 때 제공
    available_monthly_rent_financing_manwon: (
        float | None
    ) = None

    estimated_monthly_interest_if_used_manwon: (
        float | None
    ) = None

    # 금융상품을 적용/미적용한 이유
    selection_reason: str | None = None

    missing_fields: list[str]

    official_url: str | None

    disclaimer: str


class StressTestResponse(StrictModel):
    interest_rate_increase_pct_point: float

    base_loan_interest_manwon: (
        float | None
    ) = None

    additional_monthly_interest_manwon: float

    stressed_loan_interest_manwon: (
        float | None
    ) = None

    stressed_total_monthly_cost_manwon: float

    stress_scope: str | None = None

    calculation_note: str | None = None


class FutureSimulationResponse(
    StrictModel
):
    available: bool

    scenario_feasible_at_move_in: (
        bool | None
    ) = None

    monthly_saving_capacity_manwon: (
        float | None
    ) = None

    target_monthly_savings_manwon: (
        float | None
    ) = None

    can_maintain_target_savings: (
        bool | None
    ) = None

    liquid_cash_after_move_manwon: (
        float | None
    ) = None

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


class RecommendationCardResponse(
    StrictModel
):
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

    # 1순위 / 2순위 선호지역 여부.
    # 선호지역 외이거나 입력이 없으면 None.
    district_preference_rank: (
        Literal[1, 2] | None
    ) = None

    housing_type: HousingType

    housing_type_label: str

    area_label: str

    deposit_bucket_label: str | None

    score_total: float

    score_breakdown: dict[
        str,
        float,
    ]

    judgement: JudgementResponse

    market_price: MarketPriceResponse

    initial_funds: InitialFundsResponse

    monthly_cost: MonthlyCostResponse

    policy_supports: list[
        PolicySupportResponse
    ]

    finance: FinanceSummaryResponse

    stress_test: StressTestResponse

    future_simulation: (
        FutureSimulationResponse
    )

    explanations: dict[
        str,
        str,
    ]


class HousingRecommendationResponse(
    StrictModel
):
    request_id: str

    generated_at: datetime

    engine_version: str

    recommendation_basis: str

    affordable_budget: (
        AffordableBudgetResponse
    )

    candidate_counts_before_full_scoring: (
        dict[str, int]
    )

    recommendation_count: int

    recommendations: list[
        RecommendationCardResponse
    ]

    limitations: list[str]


class HealthResponse(StrictModel):
    status: Literal[
        "ok",
    ]

    service: str

    engine_version: str