from __future__ import annotations

import json
from pathlib import Path

from ai_engine.recommenders.housing_plan_recommender_v1_1 import (
    HousingPlanRecommenderV11,
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
    recommender = HousingPlanRecommenderV11()

    user = {
        "birth_date": "2001-03-06",
        "evaluation_date": "2026-07-31",

        "contract_preference": "both",

        "preferred_housing_types": [
            "officetel",
            "row_house",
        ],

        "minimum_area_bucket": "20_30",
        "housing_funds_manwon": 3000,
        "loan_preference": "minimize",

        "allowed_district_names": None,

        "affordable_monthly_housing_cost_manwon": 72,

        "monthly_take_home_income_manwon": 280,
        "monthly_living_expense_manwon": 110,
        "monthly_debt_payment_manwon": 0,
        "target_monthly_savings_manwon": 50,

        # 이사비·중개보수·생활용품 등 초기 현금성 비용 가정
        "moving_initial_cost_manwon": 100,

        "management_fee_assumption_manwon": 8,
        "utilities_assumption_manwon": 7,

        "household_annual_income_manwon": 3600,
        "is_no_home": True,
        "all_household_members_no_home": True,
        "household_head_status": (
            "prospective_household_head"
        ),
        "is_single_household_head": True,

        # 자산심사 결과를 모르는 상태
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
        / "housing_plan_recommender_v1_1_demo.json"
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
    print("통합 주거 플랜 추천 v1.1")
    print("=" * 76)

    print(
        "계약 유형 구성:",
        result["output_balance"],
    )

    for index, recommendation in enumerate(
        result["recommendations"],
        start=1,
    ):
        finance = recommendation["finance"]

        print()
        print(
            f"[{index}] "
            f"{recommendation['district_name']} / "
            f"{recommendation['housing_type_label']} / "
            f"{recommendation['transaction_type_label']}"
        )

        print(
            "  최종 판단:",
            recommendation[
                "judgement"
            ]["label"],
        )

        print(
            "  점수:",
            recommendation[
                "score"
            ]["total"],
        )

        print(
            "  금융 적용 방식:",
            finance.get(
                "application_mode"
            ),
        )

        print(
            "  금융 상태:",
            finance.get(
                "match_status"
            ),
        )

        print(
            "  예상 총 월 주거비:",
            recommendation[
                "monthly_cost"
            ][
                "total_monthly_housing_cost_manwon"
            ],
            "만원",
        )

        print(
            "  1년 후 예상 순자산:",
            recommendation[
                "future_simulation"
            ].get(
                "projected_net_assets_after_12_months_manwon"
            ),
            "만원",
        )

    print()
    print(
        f"상세 결과 저장: {output_path}"
    )


if __name__ == "__main__":
    main()
