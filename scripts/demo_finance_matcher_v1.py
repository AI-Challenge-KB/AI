from __future__ import annotations

import json
from pathlib import Path

from ai_engine.finance.finance_matcher_v1 import (
    FinanceMatcherV1,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "finance"
    / "demo"
)


def main() -> None:
    matcher = FinanceMatcherV1()

    user = {
        "birth_date": "2001-03-06",
        "evaluation_date": "2026-07-31",

        # 프론트에서 입력받는 본인·배우자 합산 연소득
        "household_annual_income_manwon": 3600,

        # 보증금과 이사 초기비용으로 사용할 수 있는 금액
        "housing_funds_manwon": 3000,

        # 금융상품 상세 매칭을 위해 추가될 입력
        "is_no_home": True,
        "all_household_members_no_home": True,
        "household_head_status": (
            "prospective_household_head"
        ),
        "is_single_household_head": True,

        # 아직 자산심사를 확인하지 않은 상황
        "passes_fund_asset_test": None,
    }

    jeonse_property = {
        "contract_type": "jeonse",
        "housing_type": "officetel",
        "deposit_manwon": 15000,
        "monthly_rent_manwon": 0,
        "area_m2": 29.8,
        "contract_payment_ratio": 0.05,
    }

    monthly_property = {
        "contract_type": "monthly_rent",
        "housing_type": "row_house",
        "deposit_manwon": 2000,
        "monthly_rent_manwon": 55,
        "area_m2": 25.0,
        "contract_payment_ratio": 0.05,
        "landlord_type": "individual",
        "is_brokered_contract": True,
    }

    jeonse_results = matcher.match_all(
        user=user,
        property_info=jeonse_property,
    )

    monthly_results = matcher.match_all(
        user=user,
        property_info=monthly_property,
    )

    output = {
        "user": user,
        "jeonse_scenario": {
            "property": jeonse_property,
            "results": jeonse_results,
        },
        "monthly_rent_scenario": {
            "property": monthly_property,
            "results": monthly_results,
        },
    }

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIR
        / "finance_matcher_v1_demo.json"
    )

    output_path.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("=" * 76)
    print("금융상품 매칭 데모")
    print("=" * 76)

    print("\n[전세 시나리오]")

    for result in jeonse_results:
        estimate = result[
            "loan_estimate"
        ]

        print(
            f"- {result['product_name']}: "
            f"{result['match_status']}"
        )

        if (
            estimate.get(
                "calculation_status"
            )
            == "estimated"
        ):
            print(
                "  예상 대출액:",
                estimate.get(
                    "estimated_deposit_loan_manwon"
                ),
                "만원",
            )
            print(
                "  대출 후 부족액:",
                estimate.get(
                    "remaining_deposit_gap_manwon"
                ),
                "만원",
            )
            print(
                "  예상 월 이자:",
                estimate.get(
                    "estimated_monthly_interest_manwon"
                ),
                "만원",
            )

        if result["missing_fields"]:
            print(
                "  추가 확인:",
                ", ".join(
                    result["missing_fields"]
                ),
            )

    print("\n[월세 시나리오]")

    for result in monthly_results:
        estimate = result[
            "loan_estimate"
        ]

        print(
            f"- {result['product_name']}: "
            f"{result['match_status']}"
        )

        if (
            estimate.get(
                "calculation_status"
            )
            == "estimated"
        ):
            print(
                "  예상 보증금 대출액:",
                estimate.get(
                    "estimated_deposit_loan_manwon"
                ),
                "만원",
            )
            print(
                "  예상 월세금 대출 총액:",
                estimate.get(
                    "estimated_monthly_rent_loan_total_manwon"
                ),
                "만원",
            )

        if result["missing_fields"]:
            print(
                "  추가 확인:",
                ", ".join(
                    result["missing_fields"]
                ),
            )

    print()
    print(
        f"상세 결과 저장: {output_path}"
    )


if __name__ == "__main__":
    main()
