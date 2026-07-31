from __future__ import annotations

import json
from pathlib import Path

from ai_engine.recommenders.housing_plan_recommender_v1 import (
    HousingPlanRecommenderV1,
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
    recommender = (
        HousingPlanRecommenderV1()
    )

    user = {
        # ---------------------------------------------
        # 프론트 기본 입력
        # ---------------------------------------------
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

        # 실제 통근 API 연결 전에는
        # 백엔드가 추린 자치구를 넣거나 None으로 둔다.
        "allowed_district_names": None,

        # ---------------------------------------------
        # 적정 주거비 계산 결과
        # 기존 affordable_budget 계산기 결과를 넣는다.
        # ---------------------------------------------
        "affordable_monthly_housing_cost_manwon": 72,

        # 미래 자산 시뮬레이션
        "monthly_take_home_income_manwon": 280,
        "monthly_living_expense_manwon": 110,
        "monthly_debt_payment_manwon": 0,
        "target_monthly_savings_manwon": 50,

        # ---------------------------------------------
        # 관리비·공과금은 현재 임시 가정값
        # 추후 cost_assumption_master로 분리 예정
        # ---------------------------------------------
        "management_fee_assumption_manwon": 8,
        "utilities_assumption_manwon": 7,

        # ---------------------------------------------
        # 금융상품 사전 매칭 입력
        # ---------------------------------------------
        "household_annual_income_manwon": 3600,
        "is_no_home": True,
        "all_household_members_no_home": True,
        "household_head_status": (
            "prospective_household_head"
        ),
        "is_single_household_head": True,

        # 실제 자산심사를 하지 않은 상태
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
        / "housing_plan_recommender_v1_demo.json"
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
    print("통합 주거 플랜 추천 데모")
    print("=" * 76)

    print(
        "권장 월 주거비:",
        result["affordable_budget"][
            "amount_manwon"
        ],
        "만원",
    )

    print(
        "추천 결과 수:",
        result["recommendation_count"],
    )

    for index, recommendation in enumerate(
        result["recommendations"],
        start=1,
    ):
        print()
        print(
            f"[추천 {index}] "
            f"{recommendation['district_name']} / "
            f"{recommendation['housing_type_label']} / "
            f"{recommendation['transaction_type_label']}"
        )

        print(
            "  면적:",
            recommendation["area_label"],
        )

        print(
            "  보증금 중앙값:",
            recommendation[
                "market_price"
            ][
                "deposit_median_manwon"
            ],
            "만원",
        )

        print(
            "  월세 중앙값:",
            recommendation[
                "market_price"
            ][
                "monthly_rent_median_manwon"
            ],
            "만원",
        )

        print(
            "  총 월 주거비:",
            recommendation[
                "monthly_cost"
            ][
                "total_monthly_housing_cost_manwon"
            ],
            "만원",
        )

        print(
            "  적용 금융상품:",
            recommendation[
                "finance"
            ].get(
                "product_name"
            ),
        )

        print(
            "  최종 점수:",
            recommendation[
                "score"
            ]["total"],
        )

        print(
            "  최종 판단:",
            recommendation[
                "judgement"
            ]["label"],
        )

        print(
            "  설명:",
            recommendation[
                "explanations"
            ]["affordability"],
        )

    print()
    print(
        f"상세 JSON 저장: {output_path}"
    )


if __name__ == "__main__":
    main()
