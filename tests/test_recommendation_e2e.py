from ai_engine.api.schemas import (
    HousingRecommendationRequest,
)
from ai_engine.api.service import (
    create_recommendation_response,
)


def make_request(
    *,
    monthly_income=300,
    living_expense=100,
    debt_payment=0,
    target_savings=50,
    housing_funds=5000,
    contract_preference="monthly_rent",
    loan_preference="available",
    preferred_district_names=None,
    allowed_district_names=None,
    preferred_housing_types=None,
    moving_initial_cost=100,
    minimum_cash_reserve=300,
    top_n=5,
):
    if preferred_housing_types is None:
        preferred_housing_types = [
            "apartment",
            "officetel",
            "row_house",
            "single_multi_house",
        ]

    return HousingRecommendationRequest(
        user_profile={
            "birth_date": "2000-01-01",
            "evaluation_date": "2026-08-02",

            "monthly_take_home_income_manwon": (
                monthly_income
            ),

            "household_annual_income_manwon": (
                3600
                if monthly_income > 0
                else 0
            ),

            "monthly_living_expense_manwon": (
                living_expense
            ),

            "monthly_debt_payment_manwon": (
                debt_payment
            ),

            "target_monthly_savings_manwon": (
                target_savings
            ),

            "housing_funds_manwon": (
                housing_funds
            ),

            "is_no_home": True,
            "all_household_members_no_home": True,

            "household_head_status": (
                "household_head"
            ),

            "is_single_household_head": True,

            "passes_fund_asset_test": True,
        },

        housing_preference={
            "contract_preference": (
                contract_preference
            ),

            "preferred_housing_types": (
                preferred_housing_types
            ),

            "minimum_area_bucket": "any",

            "loan_preference": (
                loan_preference
            ),

            "preferred_district_names": (
                preferred_district_names
            ),

            "allowed_district_names": (
                allowed_district_names
            ),
        },

        cost_assumptions={
            "moving_initial_cost_manwon": (
                moving_initial_cost
            ),

            "minimum_cash_reserve_manwon": (
                minimum_cash_reserve
            ),

            "management_fee_assumption_manwon": 8,

            "utilities_assumption_manwon": 7,
        },

        top_n=top_n,
    )


def to_payload(response):
    return response.model_dump(
        mode="json"
    )


# =========================================================
# 1. 전체 Request -> Response 파이프라인
# =========================================================

def test_full_request_flow_returns_complete_response():
    request = make_request(
        contract_preference="monthly_rent",
        loan_preference="available",

        preferred_district_names=[
            "서울특별시 영등포구",
            "서울시 마포구",
        ],

        allowed_district_names=[
            "영등포구",
            "마포구",
        ],

        top_n=4,
    )

    response = (
        create_recommendation_response(
            request
        )
    )

    payload = to_payload(
        response
    )

    assert (
        payload["engine_version"]
        == "housing_plan_recommender_v1_2"
    )

    assert (
        payload["recommendation_count"]
        > 0
    )

    assert (
        len(payload["recommendations"])
        == payload["recommendation_count"]
    )

    for recommendation in payload[
        "recommendations"
    ]:
        # hard filter 확인
        assert recommendation[
            "district_name"
        ] in {
            "영등포구",
            "마포구",
        }

        # 정책지원 D/E가 API까지 살아있는지
        policy_codes = {
            support["support_code"]
            for support
            in recommendation[
                "policy_supports"
            ]
        }

        assert policy_codes == {
            "D",
            "E",
        }

        # 현재 정책지원은 비용에서
        # 자동 차감하지 않는다.
        for support in recommendation[
            "policy_supports"
        ]:
            assert (
                support[
                    "used_in_cost_scenario"
                ]
                is False
            )

            assert (
                support[
                    "applied_monthly_support_manwon"
                ]
                == 0.0
            )

        assert (
            "decision_confidence"
            in recommendation["finance"]
        )

        assert (
            "stress_scope"
            in recommendation["stress_test"]
        )

        assert (
            recommendation[
                "future_simulation"
            ]["available"]
            is True
        )

        assert (
            "monthly_saving_capacity_manwon"
            in recommendation[
                "future_simulation"
            ]
        )


# =========================================================
# 2. minimize + 충분한 현금
# =========================================================

def test_minimize_with_enough_cash_does_not_apply_finance():
    request = make_request(
        housing_funds=100000,

        contract_preference="monthly_rent",

        loan_preference="minimize",

        top_n=5,
    )

    payload = to_payload(
        create_recommendation_response(
            request
        )
    )

    assert (
        payload["recommendation_count"]
        > 0
    )

    for recommendation in payload[
        "recommendations"
    ]:
        finance = recommendation[
            "finance"
        ]

        assert (
            finance["applied"]
            is False
        )

        assert (
            finance[
                "estimated_loan_manwon"
            ]
            == 0.0
        )

        assert (
            finance[
                "decision_confidence"
            ]
            == "no_finance_needed"
        )


# =========================================================
# 3. no_loan + 전세 + 현금 0
# =========================================================

def test_no_loan_keeps_finance_off_when_deposit_is_insufficient():
    request = make_request(
        monthly_income=300,
        living_expense=100,
        target_savings=30,

        housing_funds=0,

        contract_preference="jeonse",

        loan_preference="no_loan",

        moving_initial_cost=0,
        minimum_cash_reserve=0,

        top_n=5,
    )

    payload = to_payload(
        create_recommendation_response(
            request
        )
    )

    recommendations = payload[
        "recommendations"
    ]

    assert len(
        recommendations
    ) > 0

    candidates_with_gap = [
        recommendation
        for recommendation
        in recommendations
        if (
            recommendation[
                "initial_funds"
            ][
                "remaining_gap_after_loan_manwon"
            ]
            > 0
        )
    ]

    # 전세 + 현금 0이므로
    # 최소 하나 이상은 보증금 부족이 있어야 한다.
    assert candidates_with_gap

    for recommendation in (
        candidates_with_gap
    ):
        assert (
            recommendation[
                "finance"
            ]["applied"]
            is False
        )

        assert (
            recommendation[
                "finance"
            ][
                "estimated_loan_manwon"
            ]
            == 0.0
        )

        assert (
            recommendation[
                "judgement"
            ]["code"]
            == "budget_exceeded"
        )


# =========================================================
# 4. 월 현금흐름 적자 hard fail
# =========================================================

def test_negative_monthly_cashflow_is_budget_exceeded_end_to_end():
    request = make_request(
        monthly_income=50,

        living_expense=100,

        debt_payment=0,

        target_savings=0,

        # 초기자금 부족 때문에 실패하는 경우와
        # 구분하기 위해 현금은 넉넉하게 둔다.
        housing_funds=100000,

        contract_preference="monthly_rent",

        loan_preference="minimize",

        top_n=5,
    )

    payload = to_payload(
        create_recommendation_response(
            request
        )
    )

    assert (
        payload["recommendation_count"]
        > 0
    )

    for recommendation in payload[
        "recommendations"
    ]:
        simulation = recommendation[
            "future_simulation"
        ]

        assert (
            simulation["available"]
            is True
        )

        assert (
            simulation[
                "monthly_saving_capacity_manwon"
            ]
            < 0
        )

        assert (
            recommendation[
                "judgement"
            ]["code"]
            == "budget_exceeded"
        )


# =========================================================
# 5. 지역 1순위/2순위 정보가 API까지 유지되는지
# =========================================================

def test_preferred_district_priority_survives_full_api_flow():
    request = make_request(
        housing_funds=10000,

        contract_preference="monthly_rent",

        loan_preference="minimize",

        preferred_district_names=[
            "서울특별시 영등포구",
            "서울시 마포구",
        ],

        allowed_district_names=[
            "영등포구",
            "마포구",
        ],

        top_n=5,
    )

    payload = to_payload(
        create_recommendation_response(
            request
        )
    )

    recommendations = payload[
        "recommendations"
    ]

    assert recommendations

    seen_districts = set()

    for recommendation in recommendations:
        district = recommendation[
            "district_name"
        ]

        rank = recommendation[
            "district_preference_rank"
        ]

        seen_districts.add(
            district
        )

        if district == "영등포구":
            assert rank == 1

        elif district == "마포구":
            assert rank == 2

        else:
            raise AssertionError(
                f"hard filter 밖의 지역 반환: {district}"
            )

    # 두 지역 모두 실제 시장 데이터에 존재한다면
    # diversification에 의해 둘 다 노출되어야 한다.
    assert "영등포구" in seen_districts
    assert "마포구" in seen_districts


# =========================================================
# 6. Stress test와 현재 cost scenario의 일관성
# =========================================================

def test_stress_test_is_consistent_with_finance_application():
    request = make_request(
        housing_funds=5000,

        contract_preference="both",

        loan_preference="available",

        top_n=5,
    )

    payload = to_payload(
        create_recommendation_response(
            request
        )
    )

    for recommendation in payload[
        "recommendations"
    ]:
        finance = recommendation[
            "finance"
        ]

        stress = recommendation[
            "stress_test"
        ]

        current_cost = recommendation[
            "monthly_cost"
        ][
            "total_monthly_housing_cost_manwon"
        ]

        if not finance["applied"]:
            assert (
                stress[
                    "additional_monthly_interest_manwon"
                ]
                == 0.0
            )

            assert (
                stress[
                    "stressed_total_monthly_cost_manwon"
                ]
                == current_cost
            )

            assert (
                stress["stress_scope"]
                == "no_applied_finance"
            )

        else:
            assert (
                stress[
                    "stressed_total_monthly_cost_manwon"
                ]
                >= current_cost
            )

            assert (
                stress[
                    "additional_monthly_interest_manwon"
                ]
                >= 0.0
            )
