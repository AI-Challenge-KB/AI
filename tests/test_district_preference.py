import pandas as pd

from ai_engine.recommenders.housing_plan_recommender_v1 import (
    HousingPlanRecommenderV1,
    normalize_preferred_district_names,
)


def test_preferred_districts_keep_priority_order():
    result = normalize_preferred_district_names(
        [
            "서울특별시 영등포구",
            "서울시 마포구",
        ]
    )

    assert result == [
        "영등포구",
        "마포구",
    ]


def test_first_preference_gets_10_points():
    user = {
        "preferred_district_names": [
            "영등포구",
            "마포구",
        ]
    }

    score, rank = (
        HousingPlanRecommenderV1
        ._district_preference_score(
            district_name="영등포구",
            user=user,
        )
    )

    assert score == 10.0
    assert rank == 1


def test_second_preference_gets_7_points():
    user = {
        "preferred_district_names": [
            "영등포구",
            "마포구",
        ]
    }

    score, rank = (
        HousingPlanRecommenderV1
        ._district_preference_score(
            district_name="마포구",
            user=user,
        )
    )

    assert score == 7.0
    assert rank == 2


def test_non_preferred_district_gets_zero_points():
    user = {
        "preferred_district_names": [
            "영등포구",
            "마포구",
        ]
    }

    score, rank = (
        HousingPlanRecommenderV1
        ._district_preference_score(
            district_name="강남구",
            user=user,
        )
    )

    assert score == 0.0
    assert rank is None


def test_first_preference_has_no_rough_penalty():
    user = {
        "preferred_district_names": [
            "영등포구",
            "마포구",
        ]
    }

    penalty = (
        HousingPlanRecommenderV1
        ._district_preference_penalty(
            district_name="영등포구",
            user=user,
        )
    )

    assert penalty == 0.0


def test_second_preference_has_small_rough_penalty():
    user = {
        "preferred_district_names": [
            "영등포구",
            "마포구",
        ]
    }

    penalty = (
        HousingPlanRecommenderV1
        ._district_preference_penalty(
            district_name="마포구",
            user=user,
        )
    )

    assert penalty == 0.06


def test_non_preferred_district_has_rough_penalty():
    user = {
        "preferred_district_names": [
            "영등포구",
            "마포구",
        ]
    }

    penalty = (
        HousingPlanRecommenderV1
        ._district_preference_penalty(
            district_name="강남구",
            user=user,
        )
    )

    assert penalty == 0.20


def test_no_preference_has_no_rough_penalty():
    user = {}

    penalty = (
        HousingPlanRecommenderV1
        ._district_preference_penalty(
            district_name="강남구",
            user=user,
        )
    )

    assert penalty == 0.0


def test_rough_ranking_prefers_district_priority():
    recommender = (
        HousingPlanRecommenderV1.__new__(
            HousingPlanRecommenderV1
        )
    )

    recommender.monthly_summary = pd.DataFrame(
        [
            {
                "district_code": "11560",
                "district_name": "영등포구",
                "_normalized_district_name": "영등포구",
                "housing_type": "officetel",
                "front_area_bucket": "20_30",
                "market_area_bucket": "20_30",
                "deposit_bucket": "1000_3000",
                "contract_count": 100,
                "deposit_median_manwon": 1000,
                "monthly_rent_median_manwon": 50,
                "confidence": "high",
                "is_recommendation_usable": True,
            },
            {
                "district_code": "11440",
                "district_name": "마포구",
                "_normalized_district_name": "마포구",
                "housing_type": "officetel",
                "front_area_bucket": "20_30",
                "market_area_bucket": "20_30",
                "deposit_bucket": "1000_3000",
                "contract_count": 100,
                "deposit_median_manwon": 1000,
                "monthly_rent_median_manwon": 50,
                "confidence": "high",
                "is_recommendation_usable": True,
            },
            {
                "district_code": "11680",
                "district_name": "강남구",
                "_normalized_district_name": "강남구",
                "housing_type": "officetel",
                "front_area_bucket": "20_30",
                "market_area_bucket": "20_30",
                "deposit_bucket": "1000_3000",
                "contract_count": 100,
                "deposit_median_manwon": 1000,
                "monthly_rent_median_manwon": 50,
                "confidence": "high",
                "is_recommendation_usable": True,
            },
        ]
    )

    user = {
        "preferred_housing_types": [
            "officetel",
        ],
        "minimum_area_bucket": "20_30",
        "preferred_district_names": [
            "영등포구",
            "마포구",
        ],
        "deposit_allocable_cash_manwon": 1000,
        "management_fee_assumption_manwon": 8,
        "utilities_assumption_manwon": 7,
    }

    result = (
        recommender._get_market_candidates(
            transaction_type="monthly_rent",
            user=user,
            affordable_budget=100,
        )
    )

    assert result[
        "district_name"
    ].tolist() == [
        "영등포구",
        "마포구",
        "강남구",
    ]

    assert result[
        "_rough_district_preference_penalty"
    ].tolist() == [
        0.0,
        0.06,
        0.20,
    ]
