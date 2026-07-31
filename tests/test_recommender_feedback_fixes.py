import pytest

from ai_engine.recommenders.housing_plan_recommender_v1 import (
    MINIMUM_AREA_ALLOWED_BUCKETS,
    _finance_option_sort_key,
)
from ai_engine.recommenders.housing_plan_recommender_v1_2 import (
    HousingPlanRecommenderV12,
)


def _make_finance_option(
    product_id: str,
    remaining_gap_manwon: float,
    annual_rate_pct: float,
    monthly_interest_manwon: float,
) -> dict:
    return {
        "product_id": product_id,
        "remaining_gap_manwon": (
            remaining_gap_manwon
        ),
        "monthly_interest_manwon": (
            monthly_interest_manwon
        ),
        "loan_estimate": {
            "applied_annual_rate_pct": (
                annual_rate_pct
            ),
        },
    }


def test_lower_rate_selected_when_both_fully_fund():
    options = [
        _make_finance_option(
            product_id="high_rate",
            remaining_gap_manwon=0.0,
            annual_rate_pct=3.8,
            monthly_interest_manwon=20.0,
        ),
        _make_finance_option(
            product_id="low_rate",
            remaining_gap_manwon=0.0,
            annual_rate_pct=2.5,
            monthly_interest_manwon=14.0,
        ),
    ]

    options.sort(key=_finance_option_sort_key)

    assert options[0]["product_id"] == "low_rate"


def test_fully_funded_selected_over_lower_rate_with_gap():
    options = [
        _make_finance_option(
            product_id="fully_funded",
            remaining_gap_manwon=0.0,
            annual_rate_pct=3.8,
            monthly_interest_manwon=20.0,
        ),
        _make_finance_option(
            product_id="lower_rate_but_gap",
            remaining_gap_manwon=500.0,
            annual_rate_pct=2.5,
            monthly_interest_manwon=14.0,
        ),
    ]

    options.sort(key=_finance_option_sort_key)

    assert (
        options[0]["product_id"]
        == "fully_funded"
    )


def test_smallest_gap_selected_when_none_fully_fund():
    options = [
        _make_finance_option(
            product_id="small_gap",
            remaining_gap_manwon=300.0,
            annual_rate_pct=3.8,
            monthly_interest_manwon=20.0,
        ),
        _make_finance_option(
            product_id="large_gap",
            remaining_gap_manwon=700.0,
            annual_rate_pct=2.5,
            monthly_interest_manwon=14.0,
        ),
    ]

    options.sort(key=_finance_option_sort_key)

    assert options[0]["product_id"] == "small_gap"


@pytest.mark.parametrize(
    (
        "shortfall",
        "required",
        "expected_penalty",
    ),
    [
        (0.0, 5000.0, 0.0),
        (500.0, 5000.0, 2.5),
        (2500.0, 5000.0, 12.5),
        (5000.0, 5000.0, 25.0),
        (7000.0, 5000.0, 25.0),
    ],
)
def test_upfront_shortfall_penalty_is_proportional(
    shortfall: float,
    required: float,
    expected_penalty: float,
):
    penalty = HousingPlanRecommenderV12._calculate_upfront_shortfall_penalty(
        upfront_shortfall_manwon=shortfall,
        total_upfront_required_manwon=required,
    )

    assert penalty == pytest.approx(
        expected_penalty
    )


def test_under_20_area_filter_is_not_same_as_any():
    assert MINIMUM_AREA_ALLOWED_BUCKETS["under_20"] == [
        "under_20"
    ]

    assert MINIMUM_AREA_ALLOWED_BUCKETS["any"] == [
        "under_20",
        "20_30",
        "30_40",
        "over_40",
    ]


def test_minimum_20_area_filter_excludes_under_20():
    assert (
        "under_20"
        not in MINIMUM_AREA_ALLOWED_BUCKETS["20_30"]
    )


def test_minimum_30_area_filter():
    assert MINIMUM_AREA_ALLOWED_BUCKETS["30_40"] == [
        "30_40",
        "over_40",
    ]
