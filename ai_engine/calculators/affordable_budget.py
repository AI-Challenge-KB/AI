from ai_engine.schemas.user_profile import (
    BudgetPreference,
    UserProfile,
)


def floor_to_ten_thousand(value: float) -> int:
    """금액을 만 원 단위로 내림한다."""
    return max(0, int(value // 10_000) * 10_000)


def calculate_affordable_housing_budget(
    profile: UserProfile,
    preference: BudgetPreference,
) -> dict[str, int | float]:
    """
    사용자의 금융 프로필과 저축 유지 설정을 기준으로
    감당 가능한 월 주거비를 계산한다.
    """

    income = profile.total_monthly_income

    mandatory_cost = (
        profile.non_housing_living_expenses
        + profile.monthly_debt_payment
    )

    preserved_savings = (
        profile.target_monthly_savings
        * preference.savings_preservation_ratio
    )

    preserved_emergency_fund = (
        profile.target_emergency_fund_contribution
        * preference.emergency_fund_preservation_ratio
    )

    affordable_housing_budget = (
        income
        - mandatory_cost
        - preserved_savings
        - preserved_emergency_fund
    )

    return {
        "total_monthly_income": income,
        "mandatory_cost": mandatory_cost,
        "target_monthly_savings": (
            profile.target_monthly_savings
        ),
        "savings_preservation_ratio": (
            preference.savings_preservation_ratio
        ),
        "preserved_savings": round(preserved_savings),
        "target_emergency_fund_contribution": (
            profile.target_emergency_fund_contribution
        ),
        "emergency_fund_preservation_ratio": (
            preference.emergency_fund_preservation_ratio
        ),
        "preserved_emergency_fund": round(
            preserved_emergency_fund
        ),
        "affordable_housing_budget": (
            floor_to_ten_thousand(
                affordable_housing_budget
            )
        ),
    }