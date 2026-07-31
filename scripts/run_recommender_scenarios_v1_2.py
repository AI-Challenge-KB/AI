from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pandas as pd

from ai_engine.recommenders.housing_plan_recommender_v1_2 import (
    HousingPlanRecommenderV12,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "recommendation"
    / "scenario_validation"
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
    "passes_fund_asset_test": None,
}


SCENARIOS = [
    {
        "scenario_id": "baseline_both",
        "description": (
            "월세·전세 모두 비교, 대출 최소화"
        ),
        "updates": {},
    },
    {
        "scenario_id": "monthly_only_no_loan",
        "description": (
            "월세만 추천, 대출 사용 안 함"
        ),
        "updates": {
            "contract_preference": (
                "monthly_rent"
            ),
            "loan_preference": "no_loan",
        },
    },
    {
        "scenario_id": "jeonse_only_with_finance",
        "description": (
            "전세만 추천, 금융상품 사전 매칭"
        ),
        "updates": {
            "contract_preference": "jeonse",
            "loan_preference": "minimize",
        },
    },
    {
        "scenario_id": "jeonse_only_no_loan",
        "description": (
            "전세만 추천, 대출 사용 안 함"
        ),
        "updates": {
            "contract_preference": "jeonse",
            "loan_preference": "no_loan",
        },
    },
    {
        "scenario_id": "district_restricted",
        "description": (
            "강북구·도봉구만 추천"
        ),
        "updates": {
            "allowed_district_names": [
                "강북구",
                "도봉구",
            ],
        },
    },
    {
        "scenario_id": "over_age_limit",
        "description": (
            "청년대출 연령 조건 초과"
        ),
        "updates": {
            "birth_date": "1980-01-01",
            "contract_preference": "jeonse",
            "housing_funds_manwon": 500,
            "moving_initial_cost_manwon": 50,
            "minimum_cash_reserve_manwon": 100,
        },
    },
    {
        "scenario_id": "income_over_limit",
        "description": (
            "일반 청년대출 소득 기준 초과"
        ),
        "updates": {
            "contract_preference": "jeonse",
            "household_annual_income_manwon": (
                9000
            ),
            "housing_funds_manwon": 1000,
        },
    },
]


def validate_result(
    scenario: dict[str, Any],
    user: dict[str, Any],
    result: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    if (
        result.get("engine_version")
        != "housing_plan_recommender_v1_2"
    ):
        errors.append(
            "engine_version_mismatch"
        )

    recommendations = result.get(
        "recommendations",
        [],
    )

    if not recommendations:
        errors.append(
            "no_recommendations"
        )

        return errors

    preference = user[
        "contract_preference"
    ]

    if preference == "monthly_rent":
        if any(
            candidate["transaction_type"]
            != "monthly_rent"
            for candidate in recommendations
        ):
            errors.append(
                "monthly_preference_violation"
            )

    if preference == "jeonse":
        if any(
            candidate["transaction_type"]
            != "jeonse"
            for candidate in recommendations
        ):
            errors.append(
                "jeonse_preference_violation"
            )

    allowed_districts = user.get(
        "allowed_district_names"
    )

    if allowed_districts:
        if any(
            candidate["district_name"]
            not in allowed_districts
            for candidate in recommendations
        ):
            errors.append(
                "district_filter_violation"
            )

    for candidate in recommendations:
        funds = candidate[
            "initial_funds"
        ]

        expected_allocable = max(
            0.0,
            funds[
                "total_housing_funds_manwon"
            ]
            - funds[
                "moving_initial_cost_manwon"
            ]
            - funds[
                "minimum_cash_reserve_manwon"
            ],
        )

        actual_allocable = funds[
            "deposit_allocable_cash_manwon"
        ]

        if abs(
            expected_allocable
            - actual_allocable
        ) > 0.01:
            errors.append(
                f"{candidate['candidate_id']}:"
                "deposit_allocable_mismatch"
            )

        if (
            candidate["finance"]["applied"]
            and candidate["finance"][
                "match_status"
            ]
            == "needs_more_info"
            and candidate["judgement"]["code"]
            == "recommended"
        ):
            errors.append(
                f"{candidate['candidate_id']}:"
                "unconfirmed_finance_recommended"
            )

        upfront_shortfall = funds[
            "upfront_cash_shortfall_manwon"
        ]

        if (
            upfront_shortfall > 0
            and candidate["judgement"]["code"]
            != "budget_exceeded"
        ):
            errors.append(
                f"{candidate['candidate_id']}:"
                "shortfall_without_budget_exceeded"
            )

        if (
            candidate["score"]["total"] < 0
            or candidate["score"]["total"] > 100
        ):
            errors.append(
                f"{candidate['candidate_id']}:"
                "score_out_of_range"
            )

    return errors


def build_summary_rows(
    scenario_id: str,
    result: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = []

    for rank, candidate in enumerate(
        result["recommendations"],
        start=1,
    ):
        rows.append(
            {
                "scenario_id": scenario_id,
                "rank": rank,
                "candidate_id": candidate[
                    "candidate_id"
                ],
                "district_name": candidate[
                    "district_name"
                ],
                "housing_type": candidate[
                    "housing_type"
                ],
                "transaction_type": candidate[
                    "transaction_type"
                ],
                "area_label": candidate[
                    "area_label"
                ],
                "deposit_median_manwon": (
                    candidate[
                        "market_price"
                    ][
                        "deposit_median_manwon"
                    ]
                ),
                "monthly_rent_median_manwon": (
                    candidate[
                        "market_price"
                    ][
                        "monthly_rent_median_manwon"
                    ]
                ),
                "total_monthly_cost_manwon": (
                    candidate[
                        "monthly_cost"
                    ][
                        "total_monthly_housing_cost_manwon"
                    ]
                ),
                "affordable_budget_manwon": (
                    candidate[
                        "monthly_cost"
                    ][
                        "affordable_monthly_housing_cost_manwon"
                    ]
                ),
                "estimated_loan_manwon": (
                    candidate[
                        "initial_funds"
                    ][
                        "estimated_loan_manwon"
                    ]
                ),
                "upfront_shortfall_manwon": (
                    candidate[
                        "initial_funds"
                    ][
                        "upfront_cash_shortfall_manwon"
                    ]
                ),
                "liquid_cash_after_move_manwon": (
                    candidate[
                        "initial_funds"
                    ][
                        "liquid_cash_after_move_manwon"
                    ]
                ),
                "finance_product_name": (
                    candidate["finance"].get(
                        "product_name"
                    )
                ),
                "finance_match_status": (
                    candidate["finance"].get(
                        "match_status"
                    )
                ),
                "finance_decision_confidence": (
                    candidate["finance"].get(
                        "decision_confidence"
                    )
                ),
                "score": candidate[
                    "score"
                ]["total"],
                "judgement_code": candidate[
                    "judgement"
                ]["code"],
                "judgement_label": candidate[
                    "judgement"
                ]["label"],
            }
        )

    return rows


def main() -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    recommender = (
        HousingPlanRecommenderV12()
    )

    all_results = {}
    summary_rows = []
    validation_records = []

    print("=" * 76)
    print("주거 추천 엔진 v1.2 시나리오 검증")
    print("=" * 76)

    for scenario in SCENARIOS:
        scenario_id = scenario[
            "scenario_id"
        ]

        user = deepcopy(BASE_USER)

        user.update(
            scenario["updates"]
        )

        try:
            result = recommender.recommend(
                user=user,
                top_n=5,
            )

            errors = validate_result(
                scenario=scenario,
                user=user,
                result=result,
            )

            all_results[scenario_id] = {
                "description": scenario[
                    "description"
                ],
                "user": user,
                "result": result,
            }

            summary_rows.extend(
                build_summary_rows(
                    scenario_id=scenario_id,
                    result=result,
                )
            )

            validation_records.append(
                {
                    "scenario_id": (
                        scenario_id
                    ),
                    "description": scenario[
                        "description"
                    ],
                    "status": (
                        "passed"
                        if not errors
                        else "failed"
                    ),
                    "error_count": len(
                        errors
                    ),
                    "errors": errors,
                    "recommendation_count": (
                        result[
                            "recommendation_count"
                        ]
                    ),
                }
            )

            print(
                f"- {scenario_id}: "
                f"{'PASS' if not errors else 'FAIL'}"
            )

            for error in errors:
                print(
                    f"    · {error}"
                )

        except Exception as error:
            validation_records.append(
                {
                    "scenario_id": (
                        scenario_id
                    ),
                    "description": scenario[
                        "description"
                    ],
                    "status": "error",
                    "error_count": 1,
                    "errors": [
                        f"{type(error).__name__}: "
                        f"{error}"
                    ],
                    "recommendation_count": 0,
                }
            )

            print(
                f"- {scenario_id}: ERROR"
            )

            print(
                f"    · {type(error).__name__}: "
                f"{error}"
            )

    result_path = (
        OUTPUT_DIR
        / "scenario_results.json"
    )

    result_path.write_text(
        json.dumps(
            all_results,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    summary_path = (
        OUTPUT_DIR
        / "scenario_summary.csv"
    )

    pd.DataFrame(
        summary_rows
    ).to_csv(
        summary_path,
        index=False,
        encoding="utf-8-sig",
    )

    validation_path = (
        OUTPUT_DIR
        / "scenario_validation_report.json"
    )

    all_passed = all(
        record["status"] == "passed"
        for record in validation_records
    )

    validation_report = {
        "engine_version": (
            "housing_plan_recommender_v1_2"
        ),
        "all_passed": all_passed,
        "scenario_count": len(
            validation_records
        ),
        "passed_count": sum(
            record["status"] == "passed"
            for record in validation_records
        ),
        "failed_count": sum(
            record["status"] != "passed"
            for record in validation_records
        ),
        "scenarios": validation_records,
    }

    validation_path.write_text(
        json.dumps(
            validation_report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 76)
    print("시나리오 검증 완료")
    print("=" * 76)
    print(
        "전체 통과:",
        all_passed,
    )
    print(
        f"상세 결과: {result_path}"
    )
    print(
        f"요약 CSV: {summary_path}"
    )
    print(
        f"검증 보고서: {validation_path}"
    )


if __name__ == "__main__":
    main()
