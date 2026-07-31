from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from typing import Any
from uuid import uuid4

from ai_engine.api.schemas import (
    HousingRecommendationRequest,
    HousingRecommendationResponse,
)
from ai_engine.recommenders.housing_plan_recommender_v1_2 import (
    HousingPlanRecommenderV12,
)


RESULT_DISCLAIMER = (
    "금융상품 결과는 입력 정보와 조사된 일반 조건을 이용한 "
    "사전 추정치이며 실제 대출 승인 결과가 아닙니다."
)


@lru_cache(maxsize=1)
def get_recommender() -> HousingPlanRecommenderV12:
    """
    시장 데이터와 금융상품 마스터를 요청마다 다시 읽지 않도록
    추천 엔진 인스턴스를 프로세스 내에서 한 번만 생성한다.
    """
    return HousingPlanRecommenderV12()


def build_engine_user(
    request: HousingRecommendationRequest,
) -> dict[str, Any]:
    profile = request.user_profile
    preference = request.housing_preference
    assumptions = request.cost_assumptions

    user: dict[str, Any] = {
        "birth_date": profile.birth_date,
        "evaluation_date": (
            profile.evaluation_date
        ),

        "monthly_take_home_income_manwon": (
            profile.monthly_take_home_income_manwon
        ),

        "household_annual_income_manwon": (
            profile.household_annual_income_manwon
        ),

        "monthly_living_expense_manwon": (
            profile.monthly_living_expense_manwon
        ),

        "monthly_debt_payment_manwon": (
            profile.monthly_debt_payment_manwon
        ),

        "target_monthly_savings_manwon": (
            profile.target_monthly_savings_manwon
        ),

        "housing_funds_manwon": (
            profile.housing_funds_manwon
        ),

        "is_no_home": profile.is_no_home,

        "all_household_members_no_home": (
            profile.all_household_members_no_home
        ),

        "household_head_status": (
            profile.household_head_status
        ),

        "is_single_household_head": (
            profile.is_single_household_head
        ),

        "passes_fund_asset_test": (
            profile.passes_fund_asset_test
        ),

        "contract_preference": (
            preference.contract_preference
        ),

        "preferred_housing_types": (
            preference.preferred_housing_types
        ),

        "minimum_area_bucket": (
            preference.minimum_area_bucket
        ),

        "loan_preference": (
            preference.loan_preference
        ),

        "allowed_district_names": (
            preference.allowed_district_names
        ),

        "affordable_monthly_housing_cost_manwon": (
            assumptions
            .affordable_monthly_housing_cost_manwon
        ),

        "moving_initial_cost_manwon": (
            assumptions.moving_initial_cost_manwon
        ),

        "minimum_cash_reserve_manwon": (
            assumptions.minimum_cash_reserve_manwon
        ),

        "management_fee_assumption_manwon": (
            assumptions
            .management_fee_assumption_manwon
        ),

        "utilities_assumption_manwon": (
            assumptions.utilities_assumption_manwon
        ),
    }

    return {
        key: value
        for key, value in user.items()
        if value is not None
    }


def find_selected_product_url(
    finance: dict[str, Any],
) -> str | None:
    selected_product_id = finance.get(
        "product_id"
    )

    if not selected_product_id:
        return None

    for match in finance.get(
        "all_matches",
        [],
    ):
        if (
            match.get("product_id")
            == selected_product_id
        ):
            return match.get("official_url")

    return None


def compact_finance(
    finance: dict[str, Any],
) -> dict[str, Any]:
    return {
        "applied": bool(
            finance.get("applied")
        ),

        "product_id": finance.get(
            "product_id"
        ),

        "product_name": finance.get(
            "product_name"
        ),

        "match_status": finance.get(
            "match_status"
        ),

        "decision_confidence": finance.get(
            "decision_confidence",
            "unknown",
        ),

        "estimated_loan_manwon": float(
            finance.get(
                "estimated_loan_manwon",
                0,
            )
            or 0
        ),

        "estimated_monthly_interest_manwon": float(
            finance.get(
                "monthly_interest_manwon",
                0,
            )
            or 0
        ),

        "remaining_gap_manwon": float(
            finance.get(
                "remaining_gap_manwon",
                0,
            )
            or 0
        ),

        "missing_fields": list(
            finance.get(
                "missing_fields",
                [],
            )
        ),

        "official_url": find_selected_product_url(
            finance
        ),

        "disclaimer": RESULT_DISCLAIMER,
    }


def compact_future_simulation(
    simulation: dict[str, Any],
) -> dict[str, Any]:
    if not simulation.get(
        "available",
        False,
    ):
        return {
            "available": False,
            "reason": simulation.get(
                "reason"
            ),
        }

    return {
        "available": True,

        "scenario_feasible_at_move_in": (
            simulation.get(
                "scenario_feasible_at_move_in"
            )
        ),

        "monthly_saving_capacity_manwon": (
            simulation.get(
                "monthly_saving_capacity_manwon"
            )
        ),

        "target_monthly_savings_manwon": (
            simulation.get(
                "target_monthly_savings_manwon"
            )
        ),

        "can_maintain_target_savings": (
            simulation.get(
                "can_maintain_target_savings"
            )
        ),

        "liquid_cash_after_move_manwon": (
            simulation.get(
                "liquid_cash_after_move_manwon"
            )
        ),

        "projected_liquid_assets_after_12_months_manwon": (
            simulation.get(
                "projected_liquid_assets_after_12_months_manwon"
            )
        ),

        "projected_net_assets_after_12_months_manwon": (
            simulation.get(
                "projected_net_assets_after_12_months_manwon"
            )
        ),

        "calculation_note": simulation.get(
            "calculation_note"
        ),
    }


def compact_candidate(
    candidate: dict[str, Any],
    rank: int,
) -> dict[str, Any]:
    market = candidate["market_price"]
    funds = candidate["initial_funds"]
    monthly = candidate["monthly_cost"]

    district_name = candidate[
        "district_name"
    ]

    housing_type_label = candidate[
        "housing_type_label"
    ]

    transaction_type_label = candidate[
        "transaction_type_label"
    ]

    area_label = candidate[
        "area_label"
    ]

    title = (
        f"{district_name} "
        f"{housing_type_label} "
        f"{transaction_type_label}"
    )

    numeric_score_breakdown = {
        key: float(value)
        for key, value in candidate[
            "score"
        ].items()
        if isinstance(
            value,
            (
                int,
                float,
            ),
        )
        and key != "total"
    }

    explanations = {
        str(key): str(value)
        for key, value in candidate[
            "explanations"
        ].items()
        if value is not None
    }

    return {
        "rank": rank,

        "candidate_id": candidate[
            "candidate_id"
        ],

        "title": title,

        "transaction_type": candidate[
            "transaction_type"
        ],

        "transaction_type_label": (
            transaction_type_label
        ),

        "district_code": candidate[
            "district_code"
        ],

        "district_name": district_name,

        "housing_type": candidate[
            "housing_type"
        ],

        "housing_type_label": (
            housing_type_label
        ),

        "area_label": area_label,

        "deposit_bucket_label": (
            candidate.get(
                "deposit_bucket_label"
            )
        ),

        "score_total": float(
            candidate[
                "score"
            ]["total"]
        ),

        "score_breakdown": (
            numeric_score_breakdown
        ),

        "judgement": candidate[
            "judgement"
        ],

        "market_price": {
            "deposit_q25_manwon": (
                market.get(
                    "deposit_q25_manwon"
                )
            ),

            "deposit_median_manwon": float(
                market[
                    "deposit_median_manwon"
                ]
            ),

            "deposit_q75_manwon": (
                market.get(
                    "deposit_q75_manwon"
                )
            ),

            "monthly_rent_q25_manwon": (
                market.get(
                    "monthly_rent_q25_manwon"
                )
            ),

            "monthly_rent_median_manwon": float(
                market.get(
                    "monthly_rent_median_manwon",
                    0,
                )
                or 0
            ),

            "monthly_rent_q75_manwon": (
                market.get(
                    "monthly_rent_q75_manwon"
                )
            ),

            "contract_count": int(
                market.get(
                    "contract_count",
                    0,
                )
            ),

            "confidence": market.get(
                "confidence",
                "unknown",
            ),

            "contract_scope": market.get(
                "contract_scope"
            ),

            "data_start_date": market.get(
                "data_start_date"
            ),

            "data_end_date": market.get(
                "data_end_date"
            ),
        },

        "initial_funds": {
            "total_housing_funds_manwon": float(
                funds[
                    "total_housing_funds_manwon"
                ]
            ),

            "deposit_allocable_cash_manwon": float(
                funds[
                    "deposit_allocable_cash_manwon"
                ]
            ),

            "moving_initial_cost_manwon": float(
                funds[
                    "moving_initial_cost_manwon"
                ]
            ),

            "minimum_cash_reserve_manwon": float(
                funds[
                    "minimum_cash_reserve_manwon"
                ]
            ),

            "deposit_gap_before_loan_manwon": float(
                funds[
                    "deposit_gap_before_loan_manwon"
                ]
            ),

            "estimated_loan_manwon": float(
                funds[
                    "estimated_loan_manwon"
                ]
            ),

            "remaining_gap_after_loan_manwon": float(
                funds[
                    "remaining_gap_after_loan_manwon"
                ]
            ),

            "own_cash_required_for_deposit_manwon": float(
                funds[
                    "own_cash_required_for_deposit_manwon"
                ]
            ),

            "liquid_cash_after_move_manwon": float(
                funds[
                    "liquid_cash_after_move_manwon"
                ]
            ),

            "upfront_cash_shortfall_manwon": float(
                funds[
                    "upfront_cash_shortfall_manwon"
                ]
            ),

            "reserve_shortfall_manwon": float(
                funds[
                    "reserve_shortfall_manwon"
                ]
            ),
        },

        "monthly_cost": {
            "monthly_rent_manwon": float(
                monthly[
                    "monthly_rent_manwon"
                ]
            ),

            "management_fee_manwon": float(
                monthly[
                    "management_fee_assumption_manwon"
                ]
            ),

            "utilities_manwon": float(
                monthly[
                    "utilities_assumption_manwon"
                ]
            ),

            "loan_interest_manwon": float(
                monthly[
                    "loan_interest_manwon"
                ]
            ),

            "total_monthly_housing_cost_manwon": float(
                monthly[
                    "total_monthly_housing_cost_manwon"
                ]
            ),

            "affordable_monthly_housing_cost_manwon": float(
                monthly[
                    "affordable_monthly_housing_cost_manwon"
                ]
            ),

            "affordability_ratio": float(
                monthly[
                    "affordability_ratio"
                ]
            ),
        },

        "finance": compact_finance(
            candidate["finance"]
        ),

        "stress_test": candidate[
            "stress_test"
        ],

        "future_simulation": (
            compact_future_simulation(
                candidate[
                    "future_simulation"
                ]
            )
        ),

        "explanations": explanations,
    }


def create_recommendation_response(
    request: HousingRecommendationRequest,
) -> HousingRecommendationResponse:
    request_id = (
        request.request_id
        or str(uuid4())
    )

    engine_user = build_engine_user(
        request
    )

    engine = get_recommender()

    raw_result = engine.recommend(
        user=engine_user,
        top_n=request.top_n,
    )

    compact_recommendations = [
        compact_candidate(
            candidate=candidate,
            rank=rank,
        )
        for rank, candidate in enumerate(
            raw_result["recommendations"],
            start=1,
        )
    ]

    response_payload = {
        "request_id": request_id,

        "generated_at": datetime.now(
            timezone.utc
        ),

        "engine_version": raw_result[
            "engine_version"
        ],

        "recommendation_basis": (
            raw_result[
                "recommendation_basis"
            ]
        ),

        "affordable_budget": raw_result[
            "affordable_budget"
        ],

        "candidate_counts_before_full_scoring": (
            raw_result[
                "candidate_counts_before_full_scoring"
            ]
        ),

        "recommendation_count": len(
            compact_recommendations
        ),

        "recommendations": (
            compact_recommendations
        ),

        "limitations": raw_result[
            "limitations"
        ],
    }

    return (
        HousingRecommendationResponse
        .model_validate(
            response_payload
        )
    )
