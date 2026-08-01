from ai_engine.schemas.user_profile import (
    BudgetPreference,
    UserProfile,
)


WON_PER_MANWON = 10_000


def floor_to_ten_thousand(value: float) -> int:
    """금액을 만 원 단위로 내림한다."""
    return max(
        0,
        int(value // WON_PER_MANWON)
        * WON_PER_MANWON,
    )


def calculate_affordable_housing_budget_manwon(
    monthly_income_manwon: float,
    additional_income_manwon: float = 0.0,
    living_expense_manwon: float = 0.0,
    debt_payment_manwon: float = 0.0,
    target_savings_manwon: float = 0.0,
    savings_preservation_ratio: float = 1.0,
    target_emergency_fund_contribution_manwon: float = 0.0,
    emergency_fund_preservation_ratio: float = 1.0,
) -> dict[str, float]:
    """
    추천 API에서 사용하는 적정 월 주거비 계산의
    Single Source of Truth.

    모든 금액 단위는 만원이다.
    """

    if monthly_income_manwon < 0:
        raise ValueError(
            "monthly_income_manwon은 0 이상이어야 합니다."
        )

    if additional_income_manwon < 0:
        raise ValueError(
            "additional_income_manwon은 0 이상이어야 합니다."
        )

    non_negative_values = {
        "living_expense_manwon": (
            living_expense_manwon
        ),
        "debt_payment_manwon": (
            debt_payment_manwon
        ),
        "target_savings_manwon": (
            target_savings_manwon
        ),
        "target_emergency_fund_contribution_manwon": (
            target_emergency_fund_contribution_manwon
        ),
    }

    for field_name, value in (
        non_negative_values.items()
    ):
        if value < 0:
            raise ValueError(
                f"{field_name}은 0 이상이어야 합니다."
            )

    for field_name, ratio in {
        "savings_preservation_ratio": (
            savings_preservation_ratio
        ),
        "emergency_fund_preservation_ratio": (
            emergency_fund_preservation_ratio
        ),
    }.items():
        if not 0 <= ratio <= 1:
            raise ValueError(
                f"{field_name}은 0 이상 1 이하이어야 합니다."
            )

    total_monthly_income = (
        monthly_income_manwon
        + additional_income_manwon
    )

    mandatory_cost = (
        living_expense_manwon
        + debt_payment_manwon
    )

    preserved_savings = (
        target_savings_manwon
        * savings_preservation_ratio
    )

    preserved_emergency_fund = (
        target_emergency_fund_contribution_manwon
        * emergency_fund_preservation_ratio
    )

    affordable_housing_budget = max(
        0.0,
        total_monthly_income
        - mandatory_cost
        - preserved_savings
        - preserved_emergency_fund,
    )

    return {
        "total_monthly_income_manwon": round(
            total_monthly_income,
            2,
        ),
        "mandatory_cost_manwon": round(
            mandatory_cost,
            2,
        ),
        "preserved_savings_manwon": round(
            preserved_savings,
            2,
        ),
        "preserved_emergency_fund_manwon": round(
            preserved_emergency_fund,
            2,
        ),
        "affordable_housing_budget_manwon": round(
            affordable_housing_budget,
            2,
        ),
    }


def calculate_affordable_housing_budget(
    profile: UserProfile,
    preference: BudgetPreference,
) -> dict[str, int | float]:
    """
    기존 원 단위 UserProfile 인터페이스.

    실제 계산은 만원 단위 공통 함수에 위임한다.
    """

    result = (
        calculate_affordable_housing_budget_manwon(
            monthly_income_manwon=(
                profile.monthly_income
                / WON_PER_MANWON
            ),
            additional_income_manwon=(
                profile.additional_income
                / WON_PER_MANWON
            ),
            living_expense_manwon=(
                profile.non_housing_living_expenses
                / WON_PER_MANWON
            ),
            debt_payment_manwon=(
                profile.monthly_debt_payment
                / WON_PER_MANWON
            ),
            target_savings_manwon=(
                profile.target_monthly_savings
                / WON_PER_MANWON
            ),
            savings_preservation_ratio=(
                preference.savings_preservation_ratio
            ),
            target_emergency_fund_contribution_manwon=(
                profile.target_emergency_fund_contribution
                / WON_PER_MANWON
            ),
            emergency_fund_preservation_ratio=(
                preference
                .emergency_fund_preservation_ratio
            ),
        )
    )

    return {
        "total_monthly_income": round(
            result[
                "total_monthly_income_manwon"
            ]
            * WON_PER_MANWON
        ),
        "mandatory_cost": round(
            result["mandatory_cost_manwon"]
            * WON_PER_MANWON
        ),
        "target_monthly_savings": (
            profile.target_monthly_savings
        ),
        "savings_preservation_ratio": (
            preference.savings_preservation_ratio
        ),
        "preserved_savings": round(
            result["preserved_savings_manwon"]
            * WON_PER_MANWON
        ),
        "target_emergency_fund_contribution": (
            profile.target_emergency_fund_contribution
        ),
        "emergency_fund_preservation_ratio": (
            preference
            .emergency_fund_preservation_ratio
        ),
        "preserved_emergency_fund": round(
            result[
                "preserved_emergency_fund_manwon"
            ]
            * WON_PER_MANWON
        ),
        "affordable_housing_budget": (
            floor_to_ten_thousand(
                result[
                    "affordable_housing_budget_manwon"
                ]
                * WON_PER_MANWON
            )
        ),
    }