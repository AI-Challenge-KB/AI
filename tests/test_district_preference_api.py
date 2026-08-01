import pytest

from pydantic import ValidationError

from ai_engine.api.schemas import (
    HousingRecommendationRequest,
)
from ai_engine.api.service import (
    build_engine_user,
)


def make_request(
    preferred_district_names=None,
):
    return HousingRecommendationRequest(
        user_profile={
            "birth_date": "2000-01-01",
            "monthly_take_home_income_manwon": 300,
            "monthly_living_expense_manwon": 100,
            "monthly_debt_payment_manwon": 0,
            "target_monthly_savings_manwon": 50,
            "housing_funds_manwon": 3000,
        },
        housing_preference={
            "contract_preference": "both",
            "preferred_housing_types": [
                "officetel",
            ],
            "minimum_area_bucket": "20_30",
            "loan_preference": "minimize",
            "preferred_district_names": (
                preferred_district_names
            ),
        },
    )


def test_api_accepts_two_preferred_districts():
    request = make_request(
        [
            "영등포구",
            "마포구",
        ]
    )

    assert (
        request.housing_preference
        .preferred_district_names
        == [
            "영등포구",
            "마포구",
        ]
    )


def test_service_passes_preferred_districts_to_engine():
    request = make_request(
        [
            "서울특별시 영등포구",
            "서울시 마포구",
        ]
    )

    user = build_engine_user(
        request
    )

    assert (
        user[
            "preferred_district_names"
        ]
        == [
            "서울특별시 영등포구",
            "서울시 마포구",
        ]
    )


def test_api_rejects_more_than_two_preferred_districts():
    with pytest.raises(
        ValidationError
    ):
        make_request(
            [
                "영등포구",
                "마포구",
                "강남구",
            ]
        )


def test_missing_preferred_districts_remains_optional():
    request = make_request()

    user = build_engine_user(
        request
    )

    assert (
        "preferred_district_names"
        not in user
    )
