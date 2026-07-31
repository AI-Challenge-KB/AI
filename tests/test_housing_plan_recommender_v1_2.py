from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

import pytest

from ai_engine.recommenders.housing_plan_recommender_v1_2 import (
    HousingPlanRecommenderV12,
)


BASE_USER = {
    "birth_date": "2001-03-06",
    "evaluation_date": "2026-07-31",

    "contract_preference": "both",
    "preferred_housing_types": [
        "officetel",
        "row_house",
    ],
    "minimum_area_bucket": "20_30",

    "housing_funds_manwon": 3000,
    "moving_initial_cost_manwon": 100,
    "minimum_cash_reserve_manwon": 300,

    "loan_preference": "minimize",
    "allowed_district_names": None,

    "affordable_monthly_housing_cost_manwon": 72,

    "monthly_take_home_income_manwon": 280,
    "monthly_living_expense_manwon": 110,
    "monthly_debt_payment_manwon": 0,
    "target_monthly_savings_manwon": 50,

    "management_fee_assumption_manwon": 8,
    "utilities_assumption_manwon": 7,

    "household_annual_income_manwon": 3600,
    "is_no_home": True,
    "all_household_members_no_home": True,
    "household_head_status": (
        "prospective_household_head"
    ),
    "is_single_household_head": True,

    # 주택도시기금 자산심사 여부는 미확인
    "passes_fund_asset_test": None,
}


REQUIRED_CANDIDATE_SECTIONS = {
    "market_price",
    "initial_funds",
    "monthly_cost",
    "finance",
    "stress_test",
    "future_simulation",
    "score",
    "judgement",
    "explanations",
    "cost_scenarios",
}


def assert_nonnegative_number(
    value: Any,
    field_name: str,
) -> None:
    assert isinstance(
        value,
        (int, float),
    ), f"{field_name}가 숫자가 아닙니다: {value}"

    assert math.isfinite(
        float(value)
    ), f"{field_name}가 유한한 숫자가 아닙니다: {value}"

    assert (
        float(value) >= 0
    ), f"{field_name}가 음수입니다: {value}"


@pytest.fixture(scope="session")
def recommender() -> HousingPlanRecommenderV12:
    return HousingPlanRecommenderV12()


@pytest.fixture(scope="session")
def baseline_result(
    recommender: HousingPlanRecommenderV12,
) -> dict[str, Any]:
    return recommender.recommend(
        user=deepcopy(BASE_USER),
        top_n=5,
    )


def test_baseline_engine_version_and_count(
    baseline_result: dict[str, Any],
) -> None:
    assert (
        baseline_result["engine_version"]
        == "housing_plan_recommender_v1_2"
    )

    assert (
        baseline_result["recommendation_count"]
        == len(
            baseline_result["recommendations"]
        )
    )

    assert (
        baseline_result["recommendation_count"]
        == 5
    )


def test_both_contract_types_are_exposed(
    baseline_result: dict[str, Any],
) -> None:
    transaction_types = {
        candidate["transaction_type"]
        for candidate in baseline_result[
            "recommendations"
        ]
    }

    assert "monthly_rent" in transaction_types
    assert "jeonse" in transaction_types

    output_balance = baseline_result[
        "output_balance"
    ]

    assert (
        output_balance[
            "contract_type_diversity_applied"
        ]
        is True
    )

    assert (
        output_balance[
            "monthly_rent_count"
        ]
        + output_balance[
            "jeonse_count"
        ]
        == baseline_result[
            "recommendation_count"
        ]
    )


def test_candidate_schema_and_numeric_invariants(
    baseline_result: dict[str, Any],
) -> None:
    for candidate in baseline_result[
        "recommendations"
    ]:
        missing_sections = (
            REQUIRED_CANDIDATE_SECTIONS
            - set(candidate)
        )

        assert not missing_sections, (
            "추천 후보 필수 섹션 누락: "
            f"{sorted(missing_sections)}"
        )

        assert_nonnegative_number(
            candidate[
                "market_price"
            ][
                "deposit_median_manwon"
            ],
            "deposit_median_manwon",
        )

        assert_nonnegative_number(
            candidate[
                "monthly_cost"
            ][
                "total_monthly_housing_cost_manwon"
            ],
            "total_monthly_housing_cost_manwon",
        )

        assert_nonnegative_number(
            candidate[
                "initial_funds"
            ][
                "upfront_cash_shortfall_manwon"
            ],
            "upfront_cash_shortfall_manwon",
        )

        score = candidate["score"]["total"]

        assert 0 <= score <= 100


def test_cash_reserve_and_upfront_accounting(
    baseline_result: dict[str, Any],
) -> None:
    for candidate in baseline_result[
        "recommendations"
    ]:
        funds = candidate[
            "initial_funds"
        ]

        total_funds = funds[
            "total_housing_funds_manwon"
        ]

        moving_cost = funds[
            "moving_initial_cost_manwon"
        ]

        reserve = funds[
            "minimum_cash_reserve_manwon"
        ]

        expected_allocable = max(
            0.0,
            total_funds
            - moving_cost
            - reserve,
        )

        assert funds[
            "deposit_allocable_cash_manwon"
        ] == pytest.approx(
            expected_allocable,
            abs=0.01,
        )

        own_deposit_cash = funds[
            "own_cash_required_for_deposit_manwon"
        ]

        expected_liquid_after_move = max(
            0.0,
            total_funds
            - own_deposit_cash
            - moving_cost,
        )

        assert funds[
            "liquid_cash_after_move_manwon"
        ] == pytest.approx(
            expected_liquid_after_move,
            abs=0.01,
        )

        if (
            funds[
                "upfront_cash_shortfall_manwon"
            ]
            == 0
        ):
            assert (
                funds[
                    "liquid_cash_after_move_manwon"
                ]
                >= reserve
            )

            assert (
                funds[
                    "reserve_shortfall_manwon"
                ]
                == 0
            )


def test_unconfirmed_finance_never_becomes_recommended(
    baseline_result: dict[str, Any],
) -> None:
    provisional_candidates = [
        candidate
        for candidate in baseline_result[
            "recommendations"
        ]
        if (
            candidate["finance"]["applied"]
            and candidate["finance"][
                "match_status"
            ]
            == "needs_more_info"
        )
    ]

    assert provisional_candidates, (
        "금융상품 추가 확인이 필요한 후보가 "
        "테스트 결과에 없습니다."
    )

    for candidate in provisional_candidates:
        assert (
            candidate["judgement"]["code"]
            != "recommended"
        )

        assert (
            candidate["finance"][
                "decision_confidence"
            ]
            == "provisional_estimate"
        )

        assert (
            candidate["finance"][
                "used_in_cost_scenario"
            ]
            is True
        )

        assert (
            candidate["score"].get(
                "finance_uncertainty_penalty"
            )
            == -8.0
        )


@pytest.mark.parametrize(
    (
        "contract_preference",
        "expected_transaction_type",
    ),
    [
        (
            "monthly_rent",
            "monthly_rent",
        ),
        (
            "jeonse",
            "jeonse",
        ),
    ],
)
def test_single_contract_preference_filter(
    recommender: HousingPlanRecommenderV12,
    contract_preference: str,
    expected_transaction_type: str,
) -> None:
    user = deepcopy(BASE_USER)

    user[
        "contract_preference"
    ] = contract_preference

    result = recommender.recommend(
        user=user,
        top_n=5,
    )

    assert result["recommendations"]

    assert all(
        candidate["transaction_type"]
        == expected_transaction_type
        for candidate in result[
            "recommendations"
        ]
    )


def test_no_loan_preference_never_applies_loan(
    recommender: HousingPlanRecommenderV12,
) -> None:
    user = deepcopy(BASE_USER)

    user["loan_preference"] = "no_loan"

    result = recommender.recommend(
        user=user,
        top_n=5,
    )

    assert all(
        candidate["finance"]["applied"]
        is False
        for candidate in result[
            "recommendations"
        ]
    )

    assert all(
        candidate[
            "initial_funds"
        ][
            "estimated_loan_manwon"
        ]
        == 0
        for candidate in result[
            "recommendations"
        ]
    )

    candidates_with_shortfall = [
        candidate
        for candidate in result[
            "recommendations"
        ]
        if candidate[
            "initial_funds"
        ][
            "upfront_cash_shortfall_manwon"
        ]
        > 0
    ]

    assert candidates_with_shortfall

    assert all(
        candidate["judgement"]["code"]
        == "budget_exceeded"
        for candidate in candidates_with_shortfall
    )


def test_allowed_district_filter(
    recommender: HousingPlanRecommenderV12,
) -> None:
    user = deepcopy(BASE_USER)

    allowed_districts = {
        "강북구",
        "도봉구",
    }

    user[
        "allowed_district_names"
    ] = sorted(allowed_districts)

    result = recommender.recommend(
        user=user,
        top_n=5,
    )

    assert result["recommendations"]

    assert all(
        candidate["district_name"]
        in allowed_districts
        for candidate in result[
            "recommendations"
        ]
    )


def test_over_age_limit_has_no_applied_youth_loan(
    recommender: HousingPlanRecommenderV12,
) -> None:
    user = deepcopy(BASE_USER)

    user["birth_date"] = "1980-01-01"
    user["contract_preference"] = "jeonse"
    user["housing_funds_manwon"] = 500
    user["moving_initial_cost_manwon"] = 50
    user["minimum_cash_reserve_manwon"] = 100

    result = recommender.recommend(
        user=user,
        top_n=3,
    )

    assert result["recommendations"]

    assert all(
        candidate["finance"]["applied"]
        is False
        for candidate in result[
            "recommendations"
        ]
    )

    candidates_with_matches = [
        candidate
        for candidate in result[
            "recommendations"
        ]
        if candidate["finance"].get(
            "all_matches"
        )
    ]

    assert candidates_with_matches

    for candidate in candidates_with_matches:
        assert all(
            match["match_status"]
            == "ineligible"
            for match in candidate[
                "finance"
            ][
                "all_matches"
            ]
        )
