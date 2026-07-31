from __future__ import annotations

import json
from pathlib import Path

from ai_engine.recommenders.housing_plan_recommender_v1_2 import (
    HousingPlanRecommenderV12,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "recommendation"
    / "demo"
)


def main() -> None:
    recommender = HousingPlanRecommenderV12()

    user = {
        "birth_date": "2001-03-06",
        "evaluation_date": "2026-07-31",

        "contract_preference": "both",

        "preferred_housing_types": [
            "officetel",
            "row_house",
        ],

        "minimum_area_bucket": "20_30",

        # 보증금과 이사 초기비용으로 사용할 수 있는 전체 금액
        "housing_funds_manwon": 3000,

        # 전체 자금에서 우선 확보
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

    result = recommender.recommend(
        user=user,
        top_n=5,
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIR
        / "housing_plan_recommender_v1_2_demo.json"
    )

    output_path.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print("=" * 76)
    print("통합 주거 플랜 추천 v1.2")
    print("=" * 76)

    for index, item in enumerate(
        result["recommendations"],
        start=1,
    ):
        funds = item["initial_funds"]

        print()
        print(
            f"[{index}] "
            f"{item['district_name']} / "
            f"{item['housing_type_label']} / "
            f"{item['transaction_type_label']}"
        )

        print(
            "  최종 판단:",
            item["judgement"]["label"],
        )

        print(
            "  총 주거자금:",
            funds[
                "total_housing_funds_manwon"
            ],
            "만원",
        )

        print(
            "  보증금 가용자금:",
            funds[
                "deposit_allocable_cash_manwon"
            ],
            "만원",
        )

        print(
            "  예상 대출액:",
            funds[
                "estimated_loan_manwon"
            ],
            "만원",
        )

        print(
            "  이사 후 유동자금:",
            funds[
                "liquid_cash_after_move_manwon"
            ],
            "만원",
        )

        print(
            "  초기자금 부족액:",
            funds[
                "upfront_cash_shortfall_manwon"
            ],
            "만원",
        )

        print(
            "  금융 판단 신뢰도:",
            item["finance"].get(
                "decision_confidence"
            ),
        )

    print()
    print(
        f"상세 결과 저장: {output_path}"
    )


if __name__ == "__main__":
    main()
