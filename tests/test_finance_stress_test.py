from ai_engine.calculators.monthly_housing_cost import (
    calculate_total_monthly_housing_cost_manwon,
)
from ai_engine.recommenders.housing_plan_recommender_v1 import (
    HousingPlanRecommenderV1,
)


def test_butimok_monthly_uses_only_deposit_loan_interest():
    estimate = {
        "estimated_deposit_loan_manwon": 90,
        "deposit_loan_rate_pct": 1.3,

        # 월세금 대출까지 포함한 상한값
        "estimated_monthly_interest_upper_manwon": 0.56,
    }

    interest = (
        HousingPlanRecommenderV1
        ._extract_monthly_interest(
            estimate
        )
    )

    # 90 * 1.3% / 12 ≈ 0.10만원
    # 0.56 전체를 사용하면 안 된다.
    assert interest == 0.10


def test_standard_product_interest_is_preserved():
    estimate = {
        "estimated_deposit_loan_manwon": 1000,
        "applied_annual_rate_pct": 3.0,
        "estimated_monthly_interest_manwon": 2.5,
    }

    interest = (
        HousingPlanRecommenderV1
        ._extract_monthly_interest(
            estimate
        )
    )

    assert interest == 2.5


def test_optional_monthly_rent_interest_uses_upper_estimate():
    estimate = {
        "estimated_deposit_loan_manwon": 0,
        "estimated_monthly_rent_loan_total_manwon": 600,
        "estimated_monthly_interest_upper_manwon": 1.5,
    }

    interest = (
        HousingPlanRecommenderV1
        ._extract_monthly_rent_interest_upper(
            estimate
        )
    )

    assert interest == 1.5


def test_applied_loan_stress_recalculates_monthly_cost():
    monthly_cost = (
        calculate_total_monthly_housing_cost_manwon(
            monthly_rent_manwon=40,
            management_fee_manwon=8,
            utilities_manwon=7,
            loan_principal_manwon=1200,
            precomputed_loan_interest_manwon=3,
            own_cash_deposit_manwon=500,
        )
    )

    finance = {
        "applied": True,
        "estimated_loan_manwon": 1200,
        "monthly_interest_manwon": 3,
        "loan_estimate": {
            "estimated_deposit_loan_manwon": 1200,
            "applied_annual_rate_pct": 3.0,
        },
    }

    result = (
        HousingPlanRecommenderV1
        ._calculate_finance_stress_test(
            finance=finance,
            monthly_cost_result=monthly_cost,
            monthly_rent=40,
            management_fee=8,
            utilities=7,
            own_cash_deposit=500,
            interest_rate_increase_pct_point=2.0,
        )
    )

    # 1200만원 * 2% / 12 = 월 2만원 증가
    assert (
        result[
            "additional_monthly_interest_manwon"
        ]
        == 2.0
    )

    assert (
        result[
            "stressed_loan_interest_manwon"
        ]
        == 5.0
    )

    # 기존 59.04 → 61.04
    assert (
        result[
            "stressed_total_monthly_cost_manwon"
        ]
        == 61.04
    )

    assert (
        result["stress_scope"]
        == "applied_deposit_loan"
    )


def test_optional_finance_is_not_stressed():
    monthly_cost = (
        calculate_total_monthly_housing_cost_manwon(
            monthly_rent_manwon=40,
            management_fee_manwon=8,
            utilities_manwon=7,
            own_cash_deposit_manwon=500,
        )
    )

    finance = {
        "applied": False,
        "product_id": "monthly_loan",
        "estimated_loan_manwon": 0,
        "available_monthly_rent_financing_manwon": 600,
        "selection_reason": (
            "optional_monthly_rent_financing_available"
        ),
    }

    result = (
        HousingPlanRecommenderV1
        ._calculate_finance_stress_test(
            finance=finance,
            monthly_cost_result=monthly_cost,
            monthly_rent=40,
            management_fee=8,
            utilities=7,
            own_cash_deposit=500,
        )
    )

    assert (
        result[
            "additional_monthly_interest_manwon"
        ]
        == 0.0
    )

    assert (
        result[
            "stressed_total_monthly_cost_manwon"
        ]
        == monthly_cost[
            "net_monthly_cost_manwon"
        ]
    )

    assert (
        result["stress_scope"]
        == "no_applied_finance"
    )


def test_butimok_monthly_stress_excludes_monthly_rent_drawdown():
    monthly_cost = (
        calculate_total_monthly_housing_cost_manwon(
            monthly_rent_manwon=43,
            management_fee_manwon=8,
            utilities_manwon=7,
            loan_principal_manwon=90,
            precomputed_loan_interest_manwon=0.10,
            own_cash_deposit_manwon=3000,
        )
    )

    finance = {
        "applied": True,
        "estimated_loan_manwon": 90,
        "monthly_interest_manwon": 0.10,
        "loan_estimate": {
            "estimated_deposit_loan_manwon": 90,
            "deposit_loan_rate_pct": 1.3,
            "estimated_monthly_rent_loan_total_manwon": 1032,
            "estimated_monthly_interest_upper_manwon": 0.56,
        },
    }

    result = (
        HousingPlanRecommenderV1
        ._calculate_finance_stress_test(
            finance=finance,
            monthly_cost_result=monthly_cost,
            monthly_rent=43,
            management_fee=8,
            utilities=7,
            own_cash_deposit=3000,
        )
    )

    # 스트레스는 실제 적용된 보증금 대출 90만원에만 적용
    assert (
        result[
            "additional_monthly_interest_manwon"
        ]
        == 0.15
    )

    assert (
        result["stress_scope"]
        == (
            "applied_deposit_loan_only_"
            "monthly_rent_drawdown_excluded"
        )
    )
