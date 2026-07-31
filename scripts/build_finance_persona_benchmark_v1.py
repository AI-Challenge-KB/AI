from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "finance"
    / "persona_benchmark"
)


PRODUCT_IDS = {
    "A": "kb_youth_custom_jeonse",
    "B": "youth_butimok_jeonse",
    "C": "youth_butimok_deposit_monthly",
    "D": "youth_monthly_rent_special_support_2026",
    "E": "youth_housing_dream_savings",
}


def engine_input(
    *,
    birth_date: str,
    annual_income: float,
    housing_funds: float,
    is_no_home: bool,
    all_members_no_home: bool,
    household_head_status: str,
    is_single_household_head: bool,
    passes_asset_test: bool | None,
    contract_type: str,
    housing_type: str,
    deposit: float,
    monthly_rent: float,
    area_m2: float,
    landlord_type: str | None = None,
    is_brokered_contract: bool | None = None,
) -> dict[str, Any]:
    return {
        "user": {
            "birth_date": birth_date,
            "evaluation_date": "2026-07-31",
            "household_annual_income_manwon": annual_income,
            "housing_funds_manwon": housing_funds,
            "is_no_home": is_no_home,
            "all_household_members_no_home": (
                all_members_no_home
            ),
            "household_head_status": (
                household_head_status
            ),
            "is_single_household_head": (
                is_single_household_head
            ),
            "passes_fund_asset_test": (
                passes_asset_test
            ),
        },
        "property": {
            "contract_type": contract_type,
            "housing_type": housing_type,
            "deposit_manwon": deposit,
            "monthly_rent_manwon": monthly_rent,
            "area_m2": area_m2,
            "contract_payment_ratio": 0.05,
            "landlord_type": landlord_type,
            "is_brokered_contract": (
                is_brokered_contract
            ),
        },
    }


PERSONAS = [
    {
        "persona_id": "P01",
        "title": "무소득 인턴 대학생",
        "automation_level": "full_auto",
        "source_review_status": "clean",
        "primary_plan_code": "B",
        "secondary_plan_codes": ["A"],
        "forbidden_plan_codes": ["D"],
        "expected_primary_product_id": PRODUCT_IDS["B"],
        "expected_forbidden_product_ids": [],
        "engine_input": engine_input(
            birth_date="2003-01-01",
            annual_income=0,
            housing_funds=2400,
            is_no_home=True,
            all_members_no_home=True,
            household_head_status=(
                "prospective_household_head"
            ),
            is_single_household_head=True,
            passes_asset_test=True,
            contract_type="jeonse",
            housing_type="row_house",
            deposit=12000,
            monthly_rent=0,
            area_m2=25,
        ),
        "missing_engine_features": [],
        "review_notes": (
            "B와 A가 모두 가능할 때 예상 월 이자가 낮은 "
            "B가 우선되어야 함."
        ),
    },
    {
        "persona_id": "P02",
        "title": "중소기업 사회초년생 보증부월세",
        "automation_level": "full_auto",
        "source_review_status": "clean",
        "primary_plan_code": "C",
        "secondary_plan_codes": ["D"],
        "forbidden_plan_codes": ["A"],
        "expected_primary_product_id": PRODUCT_IDS["C"],
        "expected_forbidden_product_ids": [],
        "engine_input": engine_input(
            birth_date="2000-01-01",
            annual_income=3200,
            housing_funds=900,
            is_no_home=True,
            all_members_no_home=True,
            household_head_status="household_head",
            is_single_household_head=True,
            passes_asset_test=True,
            contract_type="monthly_rent",
            housing_type="officetel",
            deposit=3000,
            monthly_rent=60,
            area_m2=25,
            landlord_type="individual",
            is_brokered_contract=True,
        ),
        "missing_engine_features": [
            "청년월세지원 병행 추천",
        ],
        "review_notes": (
            "C의 보증금대출과 월세대출을 모두 고려해야 함."
        ),
    },
    {
        "persona_id": "P03",
        "title": "대기업 맞벌이 신혼 자산초과",
        "automation_level": "full_auto",
        "source_review_status": "clean",
        "primary_plan_code": "A",
        "secondary_plan_codes": ["E"],
        "forbidden_plan_codes": ["B"],
        "expected_primary_product_id": PRODUCT_IDS["A"],
        "expected_forbidden_product_ids": [
            PRODUCT_IDS["B"],
        ],
        "engine_input": engine_input(
            birth_date="1997-01-01",
            annual_income=6800,
            housing_funds=20000,
            is_no_home=True,
            all_members_no_home=True,
            household_head_status="household_head",
            is_single_household_head=False,
            passes_asset_test=False,
            contract_type="jeonse",
            housing_type="apartment",
            deposit=40000,
            monthly_rent=0,
            area_m2=59.9,
        ),
        "missing_engine_features": [
            "신혼 여부",
            "청약통장 별도 매칭",
        ],
        "review_notes": (
            "B는 자산심사 실패, A는 자산기준이 없어 후보."
        ),
    },
    {
        "persona_id": "P04",
        "title": "공무원 미혼 소득초과",
        "automation_level": "full_auto",
        "source_review_status": "internal_conflict",
        "primary_plan_code": "A",
        "secondary_plan_codes": [],
        "forbidden_plan_codes": ["B"],
        "expected_primary_product_id": PRODUCT_IDS["A"],
        "expected_forbidden_product_ids": [
            PRODUCT_IDS["B"],
        ],
        "engine_input": engine_input(
            birth_date="1994-01-01",
            annual_income=5800,
            housing_funds=5000,
            is_no_home=True,
            all_members_no_home=True,
            household_head_status="household_head",
            is_single_household_head=True,
            passes_asset_test=True,
            contract_type="jeonse",
            housing_type="apartment",
            deposit=25000,
            monthly_rent=0,
            area_m2=59,
        ),
        "missing_engine_features": [],
        "review_notes": (
            "요약표는 E를 2안으로 제시하지만 상세 설명은 "
            "연소득 5,800만원으로 E 가입 불가라고 설명함."
        ),
    },
    {
        "persona_id": "P05",
        "title": "병역 이행 만 35세 중소기업 재직자",
        "automation_level": "manual_review",
        "source_review_status": "ambiguous",
        "primary_plan_code": "B",
        "secondary_plan_codes": ["A"],
        "forbidden_plan_codes": [],
        "expected_primary_product_id": None,
        "expected_forbidden_product_ids": [],
        "engine_input": None,
        "missing_engine_features": [
            "병역기간 연령 차감",
            "중소기업 재직 조건",
            "신규 신청과 연장 구분",
        ],
        "review_notes": (
            "문서에서도 병역 연장 적용 범위를 은행에서 "
            "재확인해야 하는 판단 유보형 사례."
        ),
    },
    {
        "persona_id": "P06",
        "title": "만 24세 지방 소형전세",
        "automation_level": "full_auto",
        "source_review_status": "clean",
        "primary_plan_code": "B",
        "secondary_plan_codes": ["A"],
        "forbidden_plan_codes": [],
        "expected_primary_product_id": PRODUCT_IDS["B"],
        "expected_forbidden_product_ids": [],
        "engine_input": engine_input(
            birth_date="2002-01-01",
            annual_income=2200,
            housing_funds=1600,
            is_no_home=True,
            all_members_no_home=True,
            household_head_status="household_head",
            is_single_household_head=True,
            passes_asset_test=True,
            contract_type="jeonse",
            housing_type="row_house",
            deposit=8000,
            monthly_rent=0,
            area_m2=45,
        ),
        "missing_engine_features": [
            "지방 우대금리",
        ],
        "review_notes": (
            "만 25세 미만 단독세대주 60㎡·1.2억원 한도 검증."
        ),
    },
    {
        "persona_id": "P07",
        "title": "예비 신혼부부 소득특례",
        "automation_level": "manual_review",
        "source_review_status": "internal_conflict",
        "primary_plan_code": "B",
        "secondary_plan_codes": ["A"],
        "forbidden_plan_codes": [],
        "expected_primary_product_id": None,
        "expected_forbidden_product_ids": [],
        "engine_input": None,
        "missing_engine_features": [
            "신혼가구 소득 특례",
            "예비 신혼 증빙",
            "신혼가구 보증금 특례",
        ],
        "review_notes": (
            "상품 요약의 B 보증금 상한은 3억원이지만 "
            "페르소나 보증금은 3억2천만원임. "
            "신혼 특례 보증금 상한 확인 필요."
        ),
    },
    {
        "persona_id": "P08",
        "title": "미성년 자녀 3인 다자녀 가구",
        "automation_level": "manual_review",
        "source_review_status": "clean",
        "primary_plan_code": "B",
        "secondary_plan_codes": ["A"],
        "forbidden_plan_codes": ["C"],
        "expected_primary_product_id": None,
        "expected_forbidden_product_ids": [],
        "engine_input": None,
        "missing_engine_features": [
            "자녀 수",
            "다자녀 소득 특례",
            "다자녀 우대금리",
        ],
        "review_notes": (
            "현재 엔진은 일반 소득 5천만원 기준만 지원함."
        ),
    },
    {
        "persona_id": "P09",
        "title": "저소득 한부모 보증부월세",
        "automation_level": "eligibility_only",
        "source_review_status": "clean",
        "primary_plan_code": "C",
        "secondary_plan_codes": ["D"],
        "forbidden_plan_codes": ["A"],
        "expected_primary_product_id": PRODUCT_IDS["C"],
        "expected_forbidden_product_ids": [],
        "engine_input": engine_input(
            birth_date="1996-01-01",
            annual_income=3000,
            housing_funds=600,
            is_no_home=True,
            all_members_no_home=True,
            household_head_status="household_head",
            is_single_household_head=True,
            passes_asset_test=True,
            contract_type="monthly_rent",
            housing_type="row_house",
            deposit=2000,
            monthly_rent=45,
            area_m2=30,
            landlord_type="individual",
            is_brokered_contract=True,
        ),
        "missing_engine_features": [
            "한부모 여부",
            "한부모 우대금리",
            "청년월세지원 병행",
        ],
        "review_notes": (
            "C 적격성은 자동 검증 가능하나 우대금리는 검증 불가."
        ),
    },
    {
        "persona_id": "P10",
        "title": "기초생활수급자 지방 보증부월세",
        "automation_level": "eligibility_only",
        "source_review_status": "clean",
        "primary_plan_code": "C",
        "secondary_plan_codes": ["D"],
        "forbidden_plan_codes": ["A"],
        "expected_primary_product_id": PRODUCT_IDS["C"],
        "expected_forbidden_product_ids": [],
        "engine_input": engine_input(
            birth_date="1999-01-01",
            annual_income=0,
            housing_funds=150,
            is_no_home=True,
            all_members_no_home=True,
            household_head_status="household_head",
            is_single_household_head=True,
            passes_asset_test=True,
            contract_type="monthly_rent",
            housing_type="single_multi_house",
            deposit=500,
            monthly_rent=30,
            area_m2=20,
            landlord_type="individual",
            is_brokered_contract=True,
        ),
        "missing_engine_features": [
            "기초생활수급자 여부",
            "수급자 우대금리",
            "청년월세지원 병행",
        ],
        "review_notes": (
            "기본 적격성만 자동 검증하고 우대금리는 수동 검토."
        ),
    },
    {
        "persona_id": "P11",
        "title": "본인 명의 1주택 보유 청년",
        "automation_level": "full_auto",
        "source_review_status": "clean",
        "primary_plan_code": None,
        "secondary_plan_codes": [],
        "forbidden_plan_codes": [
            "A",
            "B",
            "C",
        ],
        "expected_primary_product_id": None,
        "expected_forbidden_product_ids": [
            PRODUCT_IDS["A"],
            PRODUCT_IDS["B"],
            PRODUCT_IDS["C"],
        ],
        "engine_input": engine_input(
            birth_date="1996-01-01",
            annual_income=4000,
            housing_funds=3000,
            is_no_home=False,
            all_members_no_home=False,
            household_head_status="household_head",
            is_single_household_head=True,
            passes_asset_test=True,
            contract_type="jeonse",
            housing_type="apartment",
            deposit=10000,
            monthly_rent=0,
            area_m2=40,
        ),
        "missing_engine_features": [],
        "review_notes": (
            "무주택 여부를 놓치는 오류를 검출하는 함정 사례."
        ),
    },
    {
        "persona_id": "P12",
        "title": "창업지원 수혜 예비창업자",
        "automation_level": "eligibility_only",
        "source_review_status": "clean",
        "primary_plan_code": "B",
        "secondary_plan_codes": ["A"],
        "forbidden_plan_codes": ["C"],
        "expected_primary_product_id": PRODUCT_IDS["B"],
        "expected_forbidden_product_ids": [
            PRODUCT_IDS["C"],
        ],
        "engine_input": engine_input(
            birth_date="1993-01-01",
            annual_income=4500,
            housing_funds=5000,
            is_no_home=True,
            all_members_no_home=True,
            household_head_status="household_head",
            is_single_household_head=True,
            passes_asset_test=True,
            contract_type="jeonse",
            housing_type="officetel",
            deposit=20000,
            monthly_rent=0,
            area_m2=50,
        ),
        "missing_engine_features": [
            "창업지원기관 보증 여부",
            "사업소득 산정",
        ],
        "review_notes": (
            "기본 B 적격성만 자동 검증."
        ),
    },
    {
        "persona_id": "P13",
        "title": "외국인 임대인 보증부월세",
        "automation_level": "full_auto",
        "source_review_status": "ambiguous",
        "primary_plan_code": "A",
        "secondary_plan_codes": [],
        "forbidden_plan_codes": ["C"],
        "expected_primary_product_id": PRODUCT_IDS["A"],
        "expected_forbidden_product_ids": [
            PRODUCT_IDS["C"],
        ],
        "engine_input": engine_input(
            birth_date="1999-01-01",
            annual_income=3800,
            housing_funds=1200,
            is_no_home=True,
            all_members_no_home=True,
            household_head_status="household_head",
            is_single_household_head=True,
            passes_asset_test=True,
            contract_type="monthly_rent",
            housing_type="officetel",
            deposit=4000,
            monthly_rent=65,
            area_m2=30,
            landlord_type="foreign_individual",
            is_brokered_contract=True,
        ),
        "missing_engine_features": [
            "A 상품의 전월세전환율 계산",
        ],
        "review_notes": (
            "C 외국인 임대인 배제는 자동 검증 가능. "
            "A 환산보증금 산식은 추가 구현 필요."
        ),
    },
    {
        "persona_id": "P14",
        "title": "기존 전세대출 대환",
        "automation_level": "manual_review",
        "source_review_status": "ambiguous",
        "primary_plan_code": "A",
        "secondary_plan_codes": ["B"],
        "forbidden_plan_codes": ["C"],
        "expected_primary_product_id": None,
        "expected_forbidden_product_ids": [],
        "engine_input": None,
        "missing_engine_features": [
            "기존 대출 상품",
            "기존 대출 이용기간",
            "연체 여부",
            "잔여 임대차기간",
            "대환 트랙",
        ],
        "review_notes": (
            "대환대출 전용 조건이 현재 엔진에 없음."
        ),
    },
    {
        "persona_id": "P15",
        "title": "LH 공공임대리츠 쉐어하우스",
        "automation_level": "manual_review",
        "source_review_status": "clean",
        "primary_plan_code": "B",
        "secondary_plan_codes": ["A"],
        "forbidden_plan_codes": ["C"],
        "expected_primary_product_id": None,
        "expected_forbidden_product_ids": [],
        "engine_input": None,
        "missing_engine_features": [
            "쉐어하우스 여부",
            "채권양도 협약기관",
            "세대주·면적 특례",
        ],
        "review_notes": (
            "공공기관 쉐어하우스 특례를 별도 구현해야 함."
        ),
    },
    {
        "persona_id": "P16",
        "title": "만 24세 수도권 대형 오피스텔",
        "automation_level": "full_auto",
        "source_review_status": "clean",
        "primary_plan_code": "A",
        "secondary_plan_codes": ["E"],
        "forbidden_plan_codes": ["B"],
        "expected_primary_product_id": PRODUCT_IDS["A"],
        "expected_forbidden_product_ids": [
            PRODUCT_IDS["B"],
        ],
        "engine_input": engine_input(
            birth_date="2002-01-01",
            annual_income=4200,
            housing_funds=15000,
            is_no_home=True,
            all_members_no_home=True,
            household_head_status="household_head",
            is_single_household_head=True,
            passes_asset_test=True,
            contract_type="jeonse",
            housing_type="officetel",
            deposit=35000,
            monthly_rent=0,
            area_m2=70,
        ),
        "missing_engine_features": [
            "청약통장 별도 매칭",
        ],
        "review_notes": (
            "B는 보증금 3억원과 만 25세 미만 면적 60㎡를 "
            "모두 초과하므로 부적격이어야 함."
        ),
    },
    {
        "persona_id": "P17",
        "title": "중견기업 재직 갱신계약",
        "automation_level": "manual_review",
        "source_review_status": "clean",
        "primary_plan_code": "B",
        "secondary_plan_codes": ["A"],
        "forbidden_plan_codes": ["D"],
        "expected_primary_product_id": None,
        "expected_forbidden_product_ids": [],
        "engine_input": None,
        "missing_engine_features": [
            "신규·갱신계약 구분",
            "기존 대출 잔액",
            "갱신 신청기간",
            "기한연장 상환조건",
        ],
        "review_notes": (
            "현재 엔진은 계약 유형만 보고 갱신 절차를 판단하지 못함."
        ),
    },
    {
        "persona_id": "P18",
        "title": "세대주가 아닌 세대원",
        "automation_level": "full_auto",
        "source_review_status": "ambiguous",
        "primary_plan_code": None,
        "secondary_plan_codes": [],
        "forbidden_plan_codes": [
            "A",
            "B",
            "C",
        ],
        "expected_primary_product_id": None,
        "expected_forbidden_product_ids": [
            PRODUCT_IDS["A"],
            PRODUCT_IDS["B"],
            PRODUCT_IDS["C"],
        ],
        "engine_input": engine_input(
            birth_date="1997-01-01",
            annual_income=2800,
            housing_funds=3000,
            is_no_home=True,
            all_members_no_home=True,
            household_head_status="household_member",
            is_single_household_head=False,
            passes_asset_test=True,
            contract_type="jeonse",
            housing_type="row_house",
            deposit=10000,
            monthly_rent=0,
            area_m2=30,
        ),
        "missing_engine_features": [
            "세대주 전환 예정일",
        ],
        "review_notes": (
            "현재 상태에서는 A·B·C 모두 확정 추천되면 안 됨. "
            "세대주 예정자 전환 후 재검토."
        ),
    },
]


REVIEW_ISSUES = [
    {
        "issue_id": "persona_review_001",
        "persona_id": "P04",
        "severity": "high",
        "issue": (
            "요약표는 E를 2안으로 제시하지만 상세 카드에서는 "
            "연소득 초과로 가입 불가라고 설명함."
        ),
        "required_action": (
            "E를 2안에서 삭제할지 팀원에게 확인"
        ),
    },
    {
        "issue_id": "persona_review_002",
        "persona_id": "P05",
        "severity": "high",
        "issue": (
            "A를 2안으로 제시하지만 만 35세 신규 신청 가능 여부가 "
            "상세 카드에서 불확실하다고 설명됨."
        ),
        "required_action": (
            "A의 병역 연장 및 신규 신청 연령 조건 확인"
        ),
    },
    {
        "issue_id": "persona_review_003",
        "persona_id": "P07",
        "severity": "high",
        "issue": (
            "B의 요약 보증금 상한은 3억원인데 대상 주택은 "
            "3억2천만원임."
        ),
        "required_action": (
            "신혼가구 보증금 특례 상한 확인"
        ),
    },
    {
        "issue_id": "persona_review_004",
        "persona_id": "P13",
        "severity": "medium",
        "issue": (
            "A의 전월세전환율 적용 방식과 실제 환산보증금 산식이 "
            "정리되지 않음."
        ),
        "required_action": (
            "환산보증금 계산식을 공식 자료에서 확인"
        ),
    },
]


def json_cell(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
    )


def build_coverage_matrix() -> pd.DataFrame:
    rows = []

    for persona in PERSONAS:
        rows.append(
            {
                "persona_id": persona["persona_id"],
                "title": persona["title"],
                "automation_level": (
                    persona["automation_level"]
                ),
                "source_review_status": (
                    persona["source_review_status"]
                ),
                "primary_plan_code": (
                    persona["primary_plan_code"]
                ),
                "secondary_plan_codes": json_cell(
                    persona["secondary_plan_codes"]
                ),
                "forbidden_plan_codes": json_cell(
                    persona["forbidden_plan_codes"]
                ),
                "has_engine_input": (
                    persona["engine_input"] is not None
                ),
                "missing_engine_features": json_cell(
                    persona[
                        "missing_engine_features"
                    ]
                ),
                "review_notes": persona["review_notes"],
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    benchmark_path = (
        OUTPUT_DIR
        / "finance_persona_benchmark_v1.json"
    )

    benchmark_payload = {
        "benchmark_version": (
            "finance_persona_benchmark_v1"
        ),
        "evaluation_date": "2026-07-31",
        "product_ids": PRODUCT_IDS,
        "persona_count": len(PERSONAS),
        "personas": PERSONAS,
    }

    benchmark_path.write_text(
        json.dumps(
            benchmark_payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    coverage = build_coverage_matrix()

    coverage_path = (
        OUTPUT_DIR
        / "persona_coverage_matrix.csv"
    )

    coverage.to_csv(
        coverage_path,
        index=False,
        encoding="utf-8-sig",
    )

    review_path = (
        OUTPUT_DIR
        / "persona_review_issues.csv"
    )

    pd.DataFrame(
        REVIEW_ISSUES
    ).to_csv(
        review_path,
        index=False,
        encoding="utf-8-sig",
    )

    level_counts = (
        coverage[
            "automation_level"
        ]
        .value_counts()
        .to_dict()
    )

    review_counts = (
        coverage[
            "source_review_status"
        ]
        .value_counts()
        .to_dict()
    )

    print("=" * 76)
    print("금융 페르소나 벤치마크 생성 완료")
    print("=" * 76)
    print(
        f"전체 페르소나: {len(PERSONAS)}개"
    )
    print(
        "자동화 수준:",
        level_counts,
    )
    print(
        "자료 검토 상태:",
        review_counts,
    )
    print(
        f"벤치마크 JSON: {benchmark_path}"
    )
    print(
        f"커버리지 표: {coverage_path}"
    )
    print(
        f"검토 이슈: {review_path}"
    )


if __name__ == "__main__":
    main()
