from ai_engine.recommenders.housing_plan_recommender_v1 import (
    HousingPlanRecommenderV1,
)


def test_recommender_uses_affordable_budget_ssot():
    user = {
        "monthly_take_home_income_manwon": 300,
        "monthly_living_expense_manwon": 100,
        "monthly_debt_payment_manwon": 20,
        "target_monthly_savings_manwon": 50,
    }

    budget, source = (
        HousingPlanRecommenderV1
        ._get_affordable_budget(user)
    )

    # 300 - 100 - 20 - 50 = 130
    assert budget == 130
    assert source == "affordable_budget_calculator_ssot"


def test_old_30_percent_cap_is_not_used():
    user = {
        "monthly_take_home_income_manwon": 300,
        "monthly_living_expense_manwon": 100,
        "monthly_debt_payment_manwon": 20,
        "target_monthly_savings_manwon": 50,
    }

    budget, _ = (
        HousingPlanRecommenderV1
        ._get_affordable_budget(user)
    )

    # 과거 방식이면 300 * 0.30 = 90이었음.
    assert budget == 130
    assert budget != 90


def test_explicit_budget_does_not_override_ssot():
    user = {
        "monthly_take_home_income_manwon": 300,
        "monthly_living_expense_manwon": 100,
        "monthly_debt_payment_manwon": 20,
        "target_monthly_savings_manwon": 50,

        # 과거 외부 계산값.
        "affordable_monthly_housing_cost_manwon": 72,
    }

    budget, _ = (
        HousingPlanRecommenderV1
        ._get_affordable_budget(user)
    )

    assert budget == 130
    assert budget != 72


def test_zero_income_returns_zero_affordable_budget():
    user = {
        "monthly_take_home_income_manwon": 0,
        "monthly_living_expense_manwon": 50,
        "monthly_debt_payment_manwon": 0,
        "target_monthly_savings_manwon": 0,
    }

    budget, _ = (
        HousingPlanRecommenderV1
        ._get_affordable_budget(user)
    )

    assert budget == 0


def test_additional_income_is_supported():
    user = {
        "monthly_take_home_income_manwon": 250,
        "additional_income_manwon": 50,
        "monthly_living_expense_manwon": 100,
        "monthly_debt_payment_manwon": 20,
        "target_monthly_savings_manwon": 50,
    }

    budget, _ = (
        HousingPlanRecommenderV1
        ._get_affordable_budget(user)
    )

    # 250 + 50 - 100 - 20 - 50
    assert budget == 130
