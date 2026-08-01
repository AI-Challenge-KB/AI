from ai_engine.recommenders.housing_plan_recommender_v1 import (
    HousingPlanRecommenderV1,
)
from ai_engine.recommenders.housing_plan_recommender_v1_2 import (
    HousingPlanRecommenderV12,
)


def test_cash_plan_reserves_moving_cost_and_emergency_cash():
    user = {
        "housing_funds_manwon": 3000,
        "moving_initial_cost_manwon": 100,
        "minimum_cash_reserve_manwon": 300,
    }

    result = HousingPlanRecommenderV12._get_cash_plan(
        user
    )

    assert result[
        "total_housing_funds_manwon"
    ] == 3000

    assert result[
        "deposit_allocable_cash_manwon"
    ] == 2600


def test_deposit_allocable_cash_is_preferred_over_total_funds():
    user = {
        "housing_funds_manwon": 3000,
        "deposit_allocable_cash_manwon": 2600,
    }

    result = (
        HousingPlanRecommenderV1
        ._get_deposit_allocable_cash(user)
    )

    assert result == 2600


def test_total_funds_are_used_only_as_backward_compatible_fallback():
    user = {
        "housing_funds_manwon": 3000,
    }

    result = (
        HousingPlanRecommenderV1
        ._get_deposit_allocable_cash(user)
    )

    assert result == 3000


def test_zero_allocable_cash_does_not_fall_back_to_total_funds():
    user = {
        "housing_funds_manwon": 3000,
        "deposit_allocable_cash_manwon": 0,
    }

    result = (
        HousingPlanRecommenderV1
        ._get_deposit_allocable_cash(user)
    )

    assert result == 0
