import pandas as pd
import pytest

from ai_engine.recommenders.housing_plan_recommender_v1 import (
    HousingPlanRecommenderV1,
    normalize_district_name,
)


@pytest.mark.parametrize(
    "raw_value",
    [
        "영등포구",
        " 영등포구 ",
        "서울 영등포구",
        "서울시 영등포구",
        "서울시영등포구",
        "서울특별시 영등포구",
        "서울특별시영등포구",
    ],
)
def test_yeongdeungpo_aliases_are_normalized(
    raw_value,
):
    assert (
        normalize_district_name(
            raw_value
        )
        == "영등포구"
    )


@pytest.mark.parametrize(
    "raw_value,expected",
    [
        (
            "서울특별시 강남구",
            "강남구",
        ),
        (
            "서울시 마포구",
            "마포구",
        ),
        (
            "서울 노원구",
            "노원구",
        ),
        (
            "송파구",
            "송파구",
        ),
    ],
)
def test_other_seoul_districts_are_normalized(
    raw_value,
    expected,
):
    assert (
        normalize_district_name(
            raw_value
        )
        == expected
    )


@pytest.mark.parametrize(
    "raw_value",
    [
        None,
        "",
        "부산광역시 해운대구",
        "성남시 분당구",
        "영등포",
    ],
)
def test_invalid_or_non_seoul_district_returns_none(
    raw_value,
):
    assert (
        normalize_district_name(
            raw_value
        )
        is None
    )


def test_filter_matches_normalized_district():
    dataframe = pd.DataFrame(
        {
            "district_name": [
                "영등포구",
                "강남구",
            ],
            "_normalized_district_name": [
                "영등포구",
                "강남구",
            ],
        }
    )

    user = {
        "allowed_district_names": [
            "서울특별시 영등포구"
        ]
    }

    filtered = (
        HousingPlanRecommenderV1
        ._filter_allowed_districts(
            dataframe=dataframe,
            user=user,
        )
    )

    assert len(filtered) == 1
    assert (
        filtered.iloc[0][
            "district_name"
        ]
        == "영등포구"
    )


def test_multiple_allowed_districts_are_supported():
    dataframe = pd.DataFrame(
        {
            "district_name": [
                "영등포구",
                "마포구",
                "강남구",
            ],
            "_normalized_district_name": [
                "영등포구",
                "마포구",
                "강남구",
            ],
        }
    )

    user = {
        "allowed_district_names": [
            "서울시 영등포구",
            "서울특별시 마포구",
        ]
    }

    filtered = (
        HousingPlanRecommenderV1
        ._filter_allowed_districts(
            dataframe=dataframe,
            user=user,
        )
    )

    assert set(
        filtered[
            "district_name"
        ].tolist()
    ) == {
        "영등포구",
        "마포구",
    }
