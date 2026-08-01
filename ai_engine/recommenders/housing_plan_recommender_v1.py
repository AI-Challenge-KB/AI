from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from ai_engine.finance.finance_matcher_v1 import (
    FinanceMatcherV1,
)

from ai_engine.calculators.affordable_budget import (
    calculate_affordable_housing_budget_manwon,
)

from ai_engine.calculators.monthly_housing_cost import (
    calculate_total_monthly_housing_cost_manwon,
)

from ai_engine.policy.policy_support_matcher_v1 import (
    PolicySupportMatcherV1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MARKET_DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "housing"
    / "market"
)

MONTHLY_RENT_SUMMARY_PATH = (
    MARKET_DATA_DIR
    / "monthly_rent_market_summary.csv"
)

JEONSE_SUMMARY_PATH = (
    MARKET_DATA_DIR
    / "jeonse_market_summary.csv"
)

SEOUL_DISTRICT_NAMES = {
    "강남구",
    "강동구",
    "강북구",
    "강서구",
    "관악구",
    "광진구",
    "구로구",
    "금천구",
    "노원구",
    "도봉구",
    "동대문구",
    "동작구",
    "마포구",
    "서대문구",
    "서초구",
    "성동구",
    "성북구",
    "송파구",
    "양천구",
    "영등포구",
    "용산구",
    "은평구",
    "종로구",
    "중구",
    "중랑구",
}

CONTRACT_TYPE_ALIASES = {
    "monthly_rent": "monthly_rent",
    "monthly": "monthly_rent",
    "월세": "monthly_rent",
    "jeonse": "jeonse",
    "전세": "jeonse",
    "both": "both",
    "all": "both",
    "월세·전세 모두 비교": "both",
    "월세전세모두비교": "both",
}


HOUSING_TYPE_ALIASES = {
    "apartment": "apartment",
    "아파트": "apartment",
    "officetel": "officetel",
    "오피스텔": "officetel",
    "row_house": "row_house",
    "연립·다세대": "row_house",
    "연립다세대": "row_house",
    "single_multi_house": "single_multi_house",
    "단독·다가구": "single_multi_house",
    "단독다가구": "single_multi_house",
}


HOUSING_TYPE_LABELS = {
    "apartment": "아파트",
    "officetel": "오피스텔",
    "row_house": "연립·다세대",
    "single_multi_house": "단독·다가구",
}


AREA_BUCKET_LABELS = {
    "under_20": "20㎡ 이하",
    "20_30": "20㎡ 초과~30㎡",
    "30_40": "30㎡ 초과~40㎡",
    "over_40": "40㎡ 초과",
}


MARKET_AREA_LABELS = {
    "under_20": "20㎡ 이하",
    "20_30": "20㎡ 초과~30㎡",
    "30_40": "30㎡ 초과~40㎡",
    "40_60": "40㎡ 초과~60㎡",
    "60_85": "60㎡ 초과~85㎡",
    "over_85": "85㎡ 초과",
}


AREA_UPPER_BOUND_M2 = {
    "under_20": 20.0,
    "20_30": 30.0,
    "30_40": 40.0,
    "40_60": 60.0,
    "60_85": 85.0,
    "over_85": 86.0,
}


MINIMUM_AREA_ALLOWED_BUCKETS = {
    # 면적 상관없음
    "any": [
        "under_20",
        "20_30",
        "30_40",
        "over_40",
    ],

    # 20㎡ 이하만 선택
    "under_20": [
        "under_20",
    ],

    # 최소 20㎡ 이상
    "20_30": [
        "20_30",
        "30_40",
        "over_40",
    ],

    # 최소 30㎡ 이상
    "30_40": [
        "30_40",
        "over_40",
    ],

    # 최소 40㎡ 이상
    "over_40": [
        "over_40",
    ],
}

FULL_FUNDING_GAP_TOLERANCE_MANWON = 0.01


def _safe_float(
    value: object,
    default: float = float("inf"),
) -> float:
    """숫자 변환에 실패하거나 값이 없으면 기본값을 반환한다."""
    if value is None:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_finance_option_annual_rate_pct(
    option: dict,
) -> float:
    """
    금융상품 후보에서 적용 연이율을 추출한다.

    현재 추천 결과에서는 금리가
    loan_estimate.applied_annual_rate_pct에 저장된다.
    일부 중간 객체 구조가 달라도 동작하도록 여러 위치를 확인한다.
    """
    direct_rate = option.get("applied_annual_rate_pct")

    loan_estimate = option.get("loan_estimate")
    if not isinstance(loan_estimate, dict):
        loan_estimate = {}

    nested_rate = loan_estimate.get(
        "applied_annual_rate_pct"
    )

    match = option.get("match")
    if not isinstance(match, dict):
        match = {}

    match_loan_estimate = match.get("loan_estimate")
    if not isinstance(match_loan_estimate, dict):
        match_loan_estimate = {}

    match_nested_rate = match_loan_estimate.get(
        "applied_annual_rate_pct"
    )

    for rate in (
        direct_rate,
        nested_rate,
        match_nested_rate,
    ):
        if rate is not None:
            return _safe_float(rate)

    return float("inf")


def _finance_option_sort_key(
    option: dict,
) -> tuple:
    """
    금융상품 선택 우선순위.

    1. likely_eligible 우선
    2. needs_more_info 후순위
    3. 같은 eligibility 안에서는 전액 충당 상품 우선
    4. 전액 충당이 불가능하면 남은 부족액이 작은 상품 우선
    5. 이후 낮은 금리
    6. 이후 낮은 월 이자
    """

    match_status = str(
        option.get(
            "match_status"
        )
        or ""
    )

    status_priority = (
        STATUS_PRIORITY.get(
            match_status,
            99,
        )
    )

    remaining_gap = max(
        0.0,
        _safe_float(
            option.get(
                "remaining_gap_manwon"
            ),
            default=0.0,
        ),
    )

    annual_rate = (
        _get_finance_option_annual_rate_pct(
            option
        )
    )

    monthly_interest = _safe_float(
        option.get(
            "monthly_interest_manwon"
        )
    )

    product_id = str(
        option.get(
            "product_id"
        )
        or ""
    )

    fully_funded = (
        remaining_gap
        <= FULL_FUNDING_GAP_TOLERANCE_MANWON
    )

    return (
        status_priority,

        # 전액 충당이면 0, 아니면 1
        0 if fully_funded else 1,

        # 전액 충당 상품끼리는 부족액 비교 불필요
        0.0
        if fully_funded
        else remaining_gap,

        annual_rate,
        monthly_interest,
        product_id,
    )

CONFIDENCE_SCORE = {
    "high": 15.0,
    "medium": 11.0,
    "low": 6.0,
    "very_low": 2.0,
}

DISTRICT_ROUGH_PREFERENCE_PENALTY = {
    1: 0.0,
    2: 0.06,
    None: 0.20,
}

STATUS_PRIORITY = {
    "likely_eligible": 0,
    "needs_more_info": 1,
    "ineligible": 2,
}


def is_missing(value: Any) -> bool:
    if value is None:
        return True

    if isinstance(value, str):
        return value.strip() == ""

    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def to_float(
    value: Any,
    default: float | None = None,
) -> float | None:
    if is_missing(value):
        return default

    try:
        number = float(value)

        if math.isnan(number):
            return default

        return number

    except (TypeError, ValueError):
        return default


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if is_missing(value):
        return False

    normalized = str(value).strip().lower()

    return normalized in {
        "true",
        "1",
        "yes",
        "y",
        "예",
    }


def normalize_contract_preference(
    value: Any,
) -> str:
    if is_missing(value):
        return "both"

    normalized = str(value).strip().lower()

    return CONTRACT_TYPE_ALIASES.get(
        normalized,
        normalized,
    )


def normalize_housing_types(
    values: Any,
) -> list[str]:
    if is_missing(values):
        return list(HOUSING_TYPE_LABELS)

    if isinstance(values, str):
        values = [values]

    normalized_types: list[str] = []

    for value in values:
        text = str(value).strip()

        if text in {
            "상관없음",
            "any",
            "all",
        }:
            return list(HOUSING_TYPE_LABELS)

        normalized = HOUSING_TYPE_ALIASES.get(
            text,
            text,
        )

        if normalized in HOUSING_TYPE_LABELS:
            normalized_types.append(normalized)

    return list(dict.fromkeys(normalized_types))


def normalize_district_name(
    value: Any,
) -> str | None:
    """
    서울 자치구 입력을 canonical 구 이름으로 정규화한다.

    예:
        영등포구
        서울 영등포구
        서울시 영등포구
        서울시영등포구
        서울특별시 영등포구
        서울특별시영등포구

        -> 영등포구
    """

    if is_missing(value):
        return None

    normalized = str(value).strip()

    normalized = (
        normalized
        .replace(" ", "")
        .replace("\t", "")
        .replace("\n", "")
    )

    for prefix in (
        "서울특별시",
        "서울시",
        "서울",
    ):
        if normalized.startswith(prefix):
            normalized = normalized[
                len(prefix):
            ]
            break

    if normalized in SEOUL_DISTRICT_NAMES:
        return normalized

    return None

def normalize_preferred_district_names(
    values: Any,
) -> list[str]:
    """
    사용자의 선호 지역 목록을 순서를 유지한 채
    canonical 서울 자치구 이름으로 정규화한다.

    첫 번째 값은 1순위,
    두 번째 값은 2순위로 해석한다.
    """

    if is_missing(values):
        return []

    if isinstance(values, str):
        values = [values]

    normalized_districts: list[str] = []

    for value in values:
        normalized = normalize_district_name(
            value
        )

        if normalized is None:
            continue

        if normalized not in normalized_districts:
            normalized_districts.append(
                normalized
            )

    return normalized_districts[:2]

def round_money(value: Any) -> float | None:
    number = to_float(value)

    if number is None:
        return None

    return round(number, 2)


class HousingPlanRecommenderV1:
    """
    실거래 시장 요약과 금융상품 매칭 결과를 결합한
    설명 가능한 규칙 기반 주거 플랜 추천 엔진.

    현재 버전에 포함:
    - 월세·전세 시장 가격대 조회
    - 사용자 선호 조건 필터링
    - 보증금 부족액 계산
    - 금융상품 사전 매칭
    - 예상 월 주거비 계산
    - 금리 상승 스트레스 테스트
    - 최종 추천 판정

    현재 버전에 미포함:
    - 실제 대중교통 소요시간
    - 실시간 매물
    - 공공임대 실시간 공고
    - 실제 관리비 데이터
    """

    def __init__(
        self,
        monthly_summary_path: Path = (
            MONTHLY_RENT_SUMMARY_PATH
        ),
        jeonse_summary_path: Path = (
            JEONSE_SUMMARY_PATH
        ),
    ) -> None:
        if not monthly_summary_path.exists():
            raise FileNotFoundError(
                "월세 시장 요약 데이터가 없습니다.\n"
                f"예상 경로: {monthly_summary_path}"
            )

        if not jeonse_summary_path.exists():
            raise FileNotFoundError(
                "전세 시장 요약 데이터가 없습니다.\n"
                f"예상 경로: {jeonse_summary_path}"
            )

        self.monthly_summary = pd.read_csv(
            monthly_summary_path,
            encoding="utf-8-sig",
            low_memory=False,
        )

        self.jeonse_summary = pd.read_csv(
            jeonse_summary_path,
            encoding="utf-8-sig",
            low_memory=False,
        )

        self.finance_matcher = FinanceMatcherV1()

        self._prepare_market_data()
        self._validate_market_data()

    def _prepare_market_data(self) -> None:
        for dataframe in [
            self.monthly_summary,
            self.jeonse_summary,
        ]:
            if (
                "is_recommendation_usable"
                in dataframe.columns
            ):
                dataframe[
                    "is_recommendation_usable"
                ] = dataframe[
                    "is_recommendation_usable"
                ].map(to_bool)

            if "district_code" in dataframe.columns:
                dataframe["district_code"] = (
                    dataframe["district_code"]
                    .astype("string")
                    .str.replace(
                        r"\.0$",
                        "",
                        regex=True,
                    )
                    .str.zfill(5)
                )

            if "district_name" in dataframe.columns:
                dataframe[
                    "_normalized_district_name"
                ] = dataframe[
                    "district_name"
                ].map(
                    normalize_district_name
                )

        monthly_numeric_columns = [
            "contract_count",
            "deposit_q25_manwon",
            "deposit_median_manwon",
            "deposit_q75_manwon",
            "monthly_rent_q25_manwon",
            "monthly_rent_median_manwon",
            "monthly_rent_q75_manwon",
        ]

        jeonse_numeric_columns = [
            "contract_count",
            "deposit_q25_manwon",
            "deposit_median_manwon",
            "deposit_q75_manwon",
        ]

        for column in monthly_numeric_columns:
            if column in self.monthly_summary.columns:
                self.monthly_summary[column] = (
                    pd.to_numeric(
                        self.monthly_summary[column],
                        errors="coerce",
                    )
                )

        for column in jeonse_numeric_columns:
            if column in self.jeonse_summary.columns:
                self.jeonse_summary[column] = (
                    pd.to_numeric(
                        self.jeonse_summary[column],
                        errors="coerce",
                    )
                )

    def _validate_market_data(self) -> None:
        monthly_required = {
            "district_code",
            "district_name",
            "housing_type",
            "front_area_bucket",
            "market_area_bucket",
            "deposit_bucket",
            "contract_count",
            "deposit_median_manwon",
            "monthly_rent_median_manwon",
            "confidence",
            "is_recommendation_usable",
        }

        jeonse_required = {
            "district_code",
            "district_name",
            "housing_type",
            "front_area_bucket",
            "market_area_bucket",
            "contract_count",
            "deposit_median_manwon",
            "confidence",
            "is_recommendation_usable",
        }

        missing_monthly = (
            monthly_required
            - set(self.monthly_summary.columns)
        )

        missing_jeonse = (
            jeonse_required
            - set(self.jeonse_summary.columns)
        )

        if missing_monthly:
            raise ValueError(
                "월세 시장 요약 필수 컬럼 누락: "
                f"{sorted(missing_monthly)}"
            )

        if missing_jeonse:
            raise ValueError(
                "전세 시장 요약 필수 컬럼 누락: "
                f"{sorted(missing_jeonse)}"
            )

    @staticmethod
    def _resolve_contract_types(
        preference: str,
    ) -> list[str]:
        if preference == "monthly_rent":
            return ["monthly_rent"]

        if preference == "jeonse":
            return ["jeonse"]

        return [
            "monthly_rent",
            "jeonse",
        ]

    @staticmethod
    def _resolve_area_buckets(
        minimum_area_bucket: str,
    ) -> list[str]:
        return MINIMUM_AREA_ALLOWED_BUCKETS.get(
            minimum_area_bucket,
            MINIMUM_AREA_ALLOWED_BUCKETS["any"],
        )

    def _get_policy_support_matcher(
        self,
    ) -> PolicySupportMatcherV1:
        """
        정책지원 matcher를 반환한다.

        일부 단위테스트가 __init__을 거치지 않고
        recommender를 생성하는 경우도 있으므로
        필요할 때 lazy initialization 한다.
        """

        matcher = getattr(
            self,
            "policy_support_matcher",
            None,
        )

        if matcher is None:
            matcher = (
                PolicySupportMatcherV1()
            )

            self.policy_support_matcher = (
                matcher
            )

        return matcher

    @staticmethod
    def _get_deposit_allocable_cash(
        user: Mapping[str, Any],
    ) -> float:
        """
        보증금에 실제로 사용할 수 있는 현금을 반환한다.

        deposit_allocable_cash_manwon이 있으면 이를 우선 사용하고,
        기존 V1 호출과의 하위 호환성을 위해 값이 없을 때만
        housing_funds_manwon을 사용한다.
        """

        deposit_allocable_cash = to_float(
            user.get(
                "deposit_allocable_cash_manwon"
            )
        )

        if deposit_allocable_cash is not None:
            return max(
                deposit_allocable_cash,
                0.0,
            )

        total_housing_funds = (
            to_float(
                user.get(
                    "housing_funds_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        return max(
            total_housing_funds,
            0.0,
        )

    @staticmethod
    def _get_affordable_budget(
        user: Mapping[str, Any],
    ) -> tuple[float, str]:
        """
        적정 월 주거비를 계산한다.

        적정 주거비 계산의 Single Source of Truth는
        ai_engine.calculators.affordable_budget 이다.

        외부에서 전달된
        affordable_monthly_housing_cost_manwon 값은
        계산에 사용하지 않는다.
        """

        monthly_income = to_float(
            user.get(
                "monthly_take_home_income_manwon"
            )
        )

        if monthly_income is None:
            monthly_income = to_float(
                user.get(
                    "monthly_income_manwon"
                )
            )

        if monthly_income is None:
            raise ValueError(
                "월 실수령 소득 정보가 필요합니다."
            )

        additional_income = (
            to_float(
                user.get(
                    "additional_income_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        living_expense = (
            to_float(
                user.get(
                    "monthly_living_expense_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        debt_payment = (
            to_float(
                user.get(
                    "monthly_debt_payment_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        target_savings = (
            to_float(
                user.get(
                    "target_monthly_savings_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        emergency_fund_contribution = (
            to_float(
                user.get(
                    "target_emergency_fund_contribution_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        savings_preservation_ratio = to_float(
            user.get(
                "savings_preservation_ratio"
            ),
            1.0,
        )

        if savings_preservation_ratio is None:
            savings_preservation_ratio = 1.0

        emergency_preservation_ratio = to_float(
            user.get(
                "emergency_fund_preservation_ratio"
            ),
            1.0,
        )

        if emergency_preservation_ratio is None:
            emergency_preservation_ratio = 1.0

        result = (
            calculate_affordable_housing_budget_manwon(
                monthly_income_manwon=monthly_income,
                additional_income_manwon=(
                    additional_income
                ),
                living_expense_manwon=(
                    living_expense
                ),
                debt_payment_manwon=(
                    debt_payment
                ),
                target_savings_manwon=(
                    target_savings
                ),
                savings_preservation_ratio=(
                    savings_preservation_ratio
                ),
                target_emergency_fund_contribution_manwon=(
                    emergency_fund_contribution
                ),
                emergency_fund_preservation_ratio=(
                    emergency_preservation_ratio
                ),
            )
        )

        return (
            result[
                "affordable_housing_budget_manwon"
            ],
            "affordable_budget_calculator_ssot",
        )

    @staticmethod
    def _filter_allowed_districts(
        dataframe: pd.DataFrame,
        user: Mapping[str, Any],
    ) -> pd.DataFrame:
        """
        허용 지역 입력과 시장 데이터의 지역명을
        모두 서울 자치구 canonical 이름으로 정규화한 뒤
        필터링한다.
        """

        allowed_districts = user.get(
            "allowed_district_names"
        )

        if is_missing(allowed_districts):
            return dataframe

        if isinstance(
            allowed_districts,
            str,
        ):
            allowed_districts = [
                allowed_districts
            ]

        normalized_districts: list[str] = []

        for district in allowed_districts:
            normalized = (
                normalize_district_name(
                    district
                )
            )

            if normalized is not None:
                normalized_districts.append(
                    normalized
                )

        normalized_districts = list(
            dict.fromkeys(
                normalized_districts
            )
        )

        if not normalized_districts:
            return dataframe.iloc[0:0]

        if (
            "_normalized_district_name"
            in dataframe.columns
        ):
            district_series = dataframe[
                "_normalized_district_name"
            ]
        else:
            district_series = dataframe[
                "district_name"
            ].map(
                normalize_district_name
            )

        return dataframe[
            district_series.isin(
                normalized_districts
            )
        ]

    @staticmethod
    def _calculate_pre_finance_monthly_cost(
        transaction_type: str,
        row: Mapping[str, Any],
        available_cash: float,
        management_fee: float,
        utilities: float,
    ) -> float:
        """
        금융상품을 적용하기 전 rough ranking용
        월 환산 주거비를 계산한다.

        월 주거비 계산은 최종 후보 평가와 동일하게
        monthly_housing_cost calculator를 사용한다.

        아직 금융상품이 선택되지 않은 단계이므로
        대출 원금과 대출이자는 0으로 둔다.

        보증금 기회비용은 전체 보증금이 아니라
        현재 보증금에 실제 투입 가능한 자기자금에
        대해서만 계산한다.
        """

        deposit = (
            to_float(
                row.get(
                    "deposit_median_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        if transaction_type == "monthly_rent":
            monthly_rent = (
                to_float(
                    row.get(
                        "monthly_rent_median_manwon"
                    ),
                    0.0,
                )
                or 0.0
            )
        else:
            monthly_rent = 0.0

        own_cash_deposit = min(
            max(deposit, 0.0),
            max(available_cash, 0.0),
        )

        result = (
            calculate_total_monthly_housing_cost_manwon(
                monthly_rent_manwon=monthly_rent,
                management_fee_manwon=management_fee,
                utilities_manwon=utilities,

                # rough ranking 시점에는
                # 아직 금융상품을 선택하지 않음
                loan_principal_manwon=0.0,
                precomputed_loan_interest_manwon=0.0,

                own_cash_deposit_manwon=(
                    own_cash_deposit
                ),

                commute_cost_change_manwon=0.0,
                monthly_support_manwon=0.0,
            )
        )

        return result[
            "net_monthly_cost_manwon"
        ]

    def _get_market_candidates(
        self,
        transaction_type: str,
        user: Mapping[str, Any],
        affordable_budget: float,
    ) -> pd.DataFrame:
        if transaction_type == "monthly_rent":
            candidates = (
                self.monthly_summary.copy()
            )

        else:
            candidates = (
                self.jeonse_summary.copy()
            )

        preferred_housing_types = (
            normalize_housing_types(
                user.get(
                    "preferred_housing_types"
                )
            )
        )

        allowed_area_buckets = (
            self._resolve_area_buckets(
                str(
                    user.get(
                        "minimum_area_bucket",
                        "any",
                    )
                )
            )
        )

        candidates = candidates[
            candidates[
                "is_recommendation_usable"
            ]
        ]

        candidates = candidates[
            candidates["housing_type"].isin(
                preferred_housing_types
            )
        ]

        candidates = candidates[
            candidates[
                "front_area_bucket"
            ].isin(
                allowed_area_buckets
            )
        ]

        candidates = self._filter_allowed_districts(
            dataframe=candidates,
            user=user,
        )

        candidates = candidates[
            candidates[
                "deposit_median_manwon"
            ].notna()
        ]

        if transaction_type == "monthly_rent":
            candidates = candidates[
                candidates[
                    "monthly_rent_median_manwon"
                ].notna()
            ]

        available_cash = (
            self._get_deposit_allocable_cash(
                user
            )
        )

        management_fee = (
            to_float(
                user.get(
                    "management_fee_assumption_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        utilities = (
            to_float(
                user.get(
                    "utilities_assumption_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        candidates[
            "_rough_deposit_gap"
        ] = (
            candidates[
                "deposit_median_manwon"
            ]
            - available_cash
        ).clip(lower=0)

        candidates[
            "_rough_monthly_cost"
        ] = candidates.apply(
            lambda row: (
                self._calculate_pre_finance_monthly_cost(
                    transaction_type=transaction_type,
                    row=row,
                    available_cash=available_cash,
                    management_fee=management_fee,
                    utilities=utilities,
                )
            ),
            axis=1,
        )

        budget_denominator = max(
            affordable_budget,
            1.0,
        )

        deposit_denominator = (
            candidates[
                "deposit_median_manwon"
            ]
            .clip(lower=1)
        )

        candidates[
            "_rough_budget_distance"
        ] = (
            (
                candidates[
                    "_rough_monthly_cost"
                ]
                / budget_denominator
            )
            - 0.85
        ).abs()

        candidates[
            "_rough_deposit_gap_ratio"
        ] = (
            candidates[
                "_rough_deposit_gap"
            ]
            / deposit_denominator
        )

        confidence_penalty = (
            candidates["confidence"]
            .map(
                {
                    "high": 0.0,
                    "medium": 0.1,
                    "low": 0.3,
                    "very_low": 0.6,
                }
            )
            .fillna(0.6)
        )

        candidates[
            "_rough_district_preference_penalty"
        ] = candidates.apply(
            lambda row: (
                self._district_preference_penalty(
                    district_name=row.get(
                        "district_name"
                    ),
                    user=user,
                )
            ),
            axis=1,
        )

        candidates["_rough_rank"] = (
                candidates[
                    "_rough_budget_distance"
                ]
                + candidates[
                    "_rough_deposit_gap_ratio"
                ]
                * 0.5
                + confidence_penalty
                + candidates[
                    "_rough_district_preference_penalty"
                ]
        )

        return (
            candidates
            .sort_values(
                [
                    "_rough_rank",
                    "contract_count",
                ],
                ascending=[
                    True,
                    False,
                ],
            )
            .head(300)
            .reset_index(drop=True)
        )

    @staticmethod
    def _representative_area_m2(
        market_area_bucket: str,
    ) -> float:
        return AREA_UPPER_BOUND_M2.get(
            market_area_bucket,
            40.0,
        )

    @staticmethod
    def _extract_monthly_interest(
            loan_estimate: Mapping[str, Any],
    ) -> float:
        """
        현재 추천 비용 시나리오에 실제 적용되는
        보증금 대출의 월 이자만 반환한다.

        일반 금융상품:
            estimated_monthly_interest_manwon 사용

        청년전용 버팀목 전월세대출:
            estimated_monthly_interest_upper_manwon은
            월세금 대출 이자까지 포함할 수 있으므로
            그대로 사용하지 않는다.

            대신 실제 적용된 보증금 대출액과
            deposit_loan_rate_pct를 이용해 계산한다.
        """

        standard_interest = to_float(
            loan_estimate.get(
                "estimated_monthly_interest_manwon"
            )
        )

        if standard_interest is not None:
            return max(
                standard_interest,
                0.0,
            )

        deposit_loan = (
                to_float(
                    loan_estimate.get(
                        "estimated_deposit_loan_manwon"
                    ),
                    0.0,
                )
                or 0.0
        )

        deposit_rate = to_float(
            loan_estimate.get(
                "deposit_loan_rate_pct"
            )
        )

        if (
                deposit_loan > 0
                and deposit_rate is not None
        ):
            monthly_interest = (
                    deposit_loan
                    * deposit_rate
                    / 100
                    / 12
            )

            return round(
                monthly_interest,
                2,
            )

        return 0.0

    @staticmethod
    def _extract_monthly_rent_interest_upper(
        loan_estimate: Mapping[str, Any],
    ) -> float:
        """
        available 모드에서 안내용으로 사용하는
        월세 금융 예상 이자 상한을 반환한다.

        실제 추천 비용에는 자동 적용하지 않는다.
        """

        upper_interest = to_float(
            loan_estimate.get(
                "estimated_monthly_interest_upper_manwon"
            )
        )

        if upper_interest is None:
            return 0.0

        return max(
            upper_interest,
            0.0,
        )

    @staticmethod
    def _extract_deposit_loan(
        loan_estimate: Mapping[str, Any],
    ) -> float:
        return (
            to_float(
                loan_estimate.get(
                    "estimated_deposit_loan_manwon"
                ),
                0.0,
            )
            or 0.0
        )

    @staticmethod
    def _extract_remaining_gap(
        loan_estimate: Mapping[str, Any],
        original_gap: float,
    ) -> float:
        return (
            to_float(
                loan_estimate.get(
                    "remaining_deposit_gap_manwon"
                ),
                original_gap,
            )
            or 0.0
        )

    @staticmethod
    def _extract_monthly_rent_financing(
        loan_estimate: Mapping[str, Any],
    ) -> float:
        """
        월세금 대출 등 월세 금융상품에서
        이용 가능한 총 금융금액을 추출한다.

        보증금 대출과는 별개의 값이다.
        """

        return (
            to_float(
                loan_estimate.get(
                    "estimated_monthly_rent_loan_total_manwon"
                ),
                0.0,
            )
            or 0.0
        )

    def _select_finance_option(
            self,
            user: Mapping[str, Any],
            property_info: Mapping[str, Any],
            original_gap: float,
    ) -> dict[str, Any]:
        """
        사용자 대출 선호에 따라 금융상품을 선택한다.

        no_loan:
            금융상품을 사용하지 않는다.

        minimize:
            보증금 부족액이 있을 때만
            필요한 금융상품을 선택한다.

        available:
            보증금 부족액이 있으면 금융상품을 선택하고,
            부족액이 없더라도 이용 가능한 월세 금융상품이
            있다면 선택 가능한 옵션으로 안내한다.
            단, 이 경우 실제 주거비 계산에는 적용하지 않는다.
        """

        loan_preference = str(
            user.get(
                "loan_preference",
                "available",
            )
        )

        # -------------------------------------------------
        # 1. 대출을 원하지 않는 경우
        # -------------------------------------------------

        if loan_preference in {
            "no_loan",
            "대출 없이 추천",
        }:
            return {
                "applied": False,
                "product_id": None,
                "product_name": None,
                "match_status": None,
                "estimated_loan_manwon": 0.0,
                "monthly_interest_manwon": 0.0,
                "remaining_gap_manwon": round(
                    original_gap,
                    2,
                ),
                "missing_fields": [],
                "all_matches": [],
                "selection_reason": (
                    "loan_preference_no_loan"
                ),
            }

        # -------------------------------------------------
        # 2. 대출 최소화 + 보증금 부족액 없음
        # -------------------------------------------------

        if (
                loan_preference == "minimize"
                and original_gap
                <= FULL_FUNDING_GAP_TOLERANCE_MANWON
        ):
            return {
                "applied": False,
                "product_id": None,
                "product_name": None,
                "match_status": None,
                "estimated_loan_manwon": 0.0,
                "monthly_interest_manwon": 0.0,
                "remaining_gap_manwon": 0.0,
                "missing_fields": [],
                "all_matches": [],
                "selection_reason": (
                    "no_finance_needed"
                ),
            }

        # -------------------------------------------------
        # 3. 금융상품 매칭
        # -------------------------------------------------

        matches = self.finance_matcher.match_all(
            user=user,
            property_info=property_info,
        )

        deposit_loan_options: list[
            dict[str, Any]
        ] = []

        optional_monthly_rent_options: list[
            dict[str, Any]
        ] = []

        for match in matches:
            match_status = str(
                match.get(
                    "match_status"
                )
                or ""
            )

            # 명확하게 부적격인 상품은 제외
            if match_status == "ineligible":
                continue

            estimate = match.get(
                "loan_estimate",
                {},
            )

            if not isinstance(
                    estimate,
                    Mapping,
            ):
                continue

            if (
                    estimate.get(
                        "calculation_status"
                    )
                    != "estimated"
            ):
                continue

            estimated_deposit_loan = (
                self._extract_deposit_loan(
                    estimate
                )
            )

            monthly_rent_financing = (
                self._extract_monthly_rent_financing(
                    estimate
                )
            )

            deposit_monthly_interest = (
                self._extract_monthly_interest(
                    estimate
                )
            )

            monthly_rent_interest_upper = (
                self._extract_monthly_rent_interest_upper(
                    estimate
                )
            )

            remaining_gap = (
                self._extract_remaining_gap(
                    estimate,
                    original_gap,
                )
            )

            common_option = {
                "product_id": match.get(
                    "product_id"
                ),
                "product_name": match.get(
                    "product_name"
                ),
                "match_status": (
                    match_status
                ),
                "missing_fields": (
                    match.get(
                        "missing_fields",
                        [],
                    )
                ),
                "loan_estimate": estimate,
            }

            # ---------------------------------------------
            # 보증금 대출 후보
            # ---------------------------------------------

            if estimated_deposit_loan > 0:
                deposit_loan_options.append(
                    {
                        **common_option,
                        "estimated_loan_manwon": (
                            estimated_deposit_loan
                        ),
                        "monthly_interest_manwon": (
                            deposit_monthly_interest
                        ),
                        "remaining_gap_manwon": (
                            remaining_gap
                        ),
                    }
                )

            # ---------------------------------------------
            # available 모드:
            # 보증금 부족이 없어도 월세 금융상품 안내
            # ---------------------------------------------

            if (
                    loan_preference
                    == "available"
                    and original_gap
                    <= FULL_FUNDING_GAP_TOLERANCE_MANWON
                    and monthly_rent_financing > 0
            ):
                optional_monthly_rent_options.append(
                    {
                        **common_option,

                        # 실제 비용계산에는 적용하지 않음
                        "estimated_loan_manwon": 0.0,
                        "monthly_interest_manwon": 0.0,
                        "remaining_gap_manwon": 0.0,

                        # 안내용 정보
                        "available_monthly_rent_financing_manwon": (
                            monthly_rent_financing
                        ),
                        "estimated_monthly_interest_if_used_manwon": (
                            monthly_rent_interest_upper
                        ),
                    }
                )

        # -------------------------------------------------
        # 4. 보증금 부족이 있고 사용할 대출 후보가 있는 경우
        # -------------------------------------------------

        if (
                original_gap
                > FULL_FUNDING_GAP_TOLERANCE_MANWON
                and deposit_loan_options
        ):
            deposit_loan_options.sort(
                key=_finance_option_sort_key
            )

            selected = (
                deposit_loan_options[0]
            )

            return {
                "applied": True,
                **selected,
                "all_matches": matches,
                "selection_reason": (
                    "deposit_gap_financing"
                ),
            }

        # -------------------------------------------------
        # 5. available + 보증금 부족 없음
        #    선택 가능한 월세 금융상품 안내
        # -------------------------------------------------

        if (
                loan_preference
                == "available"
                and optional_monthly_rent_options
        ):
            optional_monthly_rent_options.sort(
                key=lambda option: (
                    STATUS_PRIORITY.get(
                        str(
                            option.get(
                                "match_status"
                            )
                            or ""
                        ),
                        99,
                    ),
                    _safe_float(
                        option.get(
                            "estimated_monthly_interest_if_used_manwon"
                        )
                    ),
                    str(
                        option.get(
                            "product_id"
                        )
                        or ""
                    ),
                )
            )

            selected = (
                optional_monthly_rent_options[
                    0
                ]
            )

            return {
                "applied": False,
                **selected,
                "all_matches": matches,
                "selection_reason": (
                    "optional_monthly_rent_financing_available"
                ),
            }

        # -------------------------------------------------
        # 6. 사용 가능한 상품 없음
        # -------------------------------------------------

        return {
            "applied": False,
            "product_id": None,
            "product_name": None,
            "match_status": None,
            "estimated_loan_manwon": 0.0,
            "monthly_interest_manwon": 0.0,
            "remaining_gap_manwon": round(
                max(
                    original_gap,
                    0.0,
                ),
                2,
            ),
            "missing_fields": [],
            "all_matches": matches,
            "selection_reason": (
                "no_matching_finance_product"
            ),
        }

    @staticmethod
    def _district_preference_score(
        district_name: Any,
        user: Mapping[str, Any],
    ) -> tuple[float, int | None]:
        """
        선호 지역 순위에 따른 점수를 반환한다.

        1순위: 10점
        2순위: 7점
        그 외: 0점

        선호지역 입력이 아예 없는 경우에는
        기존 점수 체계를 유지하기 위해 10점을 반환한다.
        """

        preferred_districts = (
            normalize_preferred_district_names(
                user.get(
                    "preferred_district_names"
                )
            )
        )

        if not preferred_districts:
            return 10.0, None

        normalized_district = (
            normalize_district_name(
                district_name
            )
        )

        if normalized_district is None:
            return 0.0, None

        if (
            len(preferred_districts) >= 1
            and normalized_district
            == preferred_districts[0]
        ):
            return 10.0, 1

        if (
            len(preferred_districts) >= 2
            and normalized_district
            == preferred_districts[1]
        ):
            return 7.0, 2

        return 0.0, None

    @staticmethod
    def _district_preference_penalty(
        district_name: Any,
        user: Mapping[str, Any],
    ) -> float:
        """
        rough ranking 단계에서 사용하는
        지역 선호 penalty.

        1순위: 0.00
        2순위: 0.06
        선호지역 외: 0.20

        선호지역 입력이 없는 경우에는
        모든 지역을 동일하게 취급한다.
        """

        preferred_districts = (
            normalize_preferred_district_names(
                user.get(
                    "preferred_district_names"
                )
            )
        )

        if not preferred_districts:
            return 0.0

        normalized_district = (
            normalize_district_name(
                district_name
            )
        )

        if normalized_district is None:
            return (
                DISTRICT_ROUGH_PREFERENCE_PENALTY[
                    None
                ]
            )

        if (
            len(preferred_districts) >= 1
            and normalized_district
            == preferred_districts[0]
        ):
            return (
                DISTRICT_ROUGH_PREFERENCE_PENALTY[
                    1
                ]
            )

        if (
            len(preferred_districts) >= 2
            and normalized_district
            == preferred_districts[1]
        ):
            return (
                DISTRICT_ROUGH_PREFERENCE_PENALTY[
                    2
                ]
            )

        return (
            DISTRICT_ROUGH_PREFERENCE_PENALTY[
                None
            ]
        )

    @staticmethod
    def _affordability_score(
        monthly_cost: float,
        budget: float,
    ) -> float:
        if budget <= 0:
            return 0.0

        ratio = monthly_cost / budget

        if ratio <= 0.80:
            return 40.0

        if ratio <= 1.00:
            return round(
                40.0
                - (
                    (ratio - 0.80)
                    / 0.20
                )
                * 10.0,
                2,
            )

        if ratio <= 1.10:
            return round(
                30.0
                - (
                    (ratio - 1.00)
                    / 0.10
                )
                * 15.0,
                2,
            )

        if ratio <= 1.25:
            return round(
                15.0
                - (
                    (ratio - 1.10)
                    / 0.15
                )
                * 15.0,
                2,
            )

        return 0.0

    @staticmethod
    def _initial_funds_score(
        remaining_gap: float,
        deposit: float,
    ) -> float:
        if remaining_gap <= 0:
            return 25.0

        if deposit <= 0:
            return 0.0

        gap_ratio = remaining_gap / deposit

        if gap_ratio <= 0.05:
            return 18.0

        if gap_ratio <= 0.10:
            return 10.0

        return 0.0

    @staticmethod
    def _loan_burden_score(
        loan_amount: float,
        deposit: float,
    ) -> float:
        if loan_amount <= 0:
            return 10.0

        if deposit <= 0:
            return 0.0

        loan_ratio = loan_amount / deposit

        if loan_ratio <= 0.30:
            return 8.0

        if loan_ratio <= 0.60:
            return 5.0

        return 2.0

    @staticmethod
    def _final_judgement(
        total_score: float,
        affordability_ratio: float,
        remaining_gap: float,
    ) -> tuple[str, str]:
        if remaining_gap > 0:
            return (
                "budget_exceeded",
                "예산 초과",
            )

        if affordability_ratio > 1.20:
            return (
                "budget_exceeded",
                "예산 초과",
            )

        if (
            total_score >= 80
            and affordability_ratio <= 1.00
        ):
            return (
                "recommended",
                "추천",
            )

        if (
            total_score >= 65
            and affordability_ratio <= 1.10
        ):
            return (
                "conditionally_recommended",
                "조건부 추천",
            )

        return (
            "consider_other_area",
            "다른 지역 검토 권장",
        )

    @staticmethod
    def _future_simulation(
        user: Mapping[str, Any],
        monthly_housing_cost: float,
    ) -> dict[str, Any]:
        monthly_income = to_float(
            user.get(
                "monthly_take_home_income_manwon"
            )
        )

        if monthly_income is None:
            monthly_income = to_float(
                user.get(
                    "monthly_income_manwon"
                )
            )

        if monthly_income is None:
            return {
                "available": False,
                "reason": (
                    "월 실수령 소득 정보가 없어 "
                    "1년 후 자산을 계산하지 않음"
                ),
            }

        living_expense = (
            to_float(
                user.get(
                    "monthly_living_expense_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        debt_payment = (
            to_float(
                user.get(
                    "monthly_debt_payment_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        target_savings = (
            to_float(
                user.get(
                    "target_monthly_savings_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        current_assets = (
            to_float(
                user.get(
                    "housing_funds_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        monthly_saving_capacity = (
            monthly_income
            - living_expense
            - debt_payment
            - monthly_housing_cost
        )

        projected_assets = (
            current_assets
            + monthly_saving_capacity * 12
        )

        return {
            "available": True,
            "monthly_saving_capacity_manwon": round(
                monthly_saving_capacity,
                2,
            ),
            "target_monthly_savings_manwon": round(
                target_savings,
                2,
            ),
            "can_maintain_target_savings": (
                monthly_saving_capacity
                >= target_savings
            ),
            "projected_assets_after_12_months_manwon": round(
                projected_assets,
                2,
            ),
            "calculation_note": (
                "현재 주거자금과 매월 소득에서 생활비·대출상환액·"
                "주거비를 차감한 금액이 12개월간 유지된다고 가정"
            ),
        }

    @staticmethod
    def _calculate_finance_stress_test(
        finance: Mapping[str, Any],
        monthly_cost_result: Mapping[str, Any],
        monthly_rent: float,
        management_fee: float,
        utilities: float,
        own_cash_deposit: float,
        interest_rate_increase_pct_point: float = 2.0,
    ) -> dict[str, Any]:
        """
        현재 비용 시나리오에 실제 적용된 보증금 대출에 대해
        금리 상승 stress test를 수행한다.

        available 모드에서 안내만 하는 선택형 월세 금융상품은
        현재 비용 시나리오에 적용되지 않았으므로
        stress test 대상에서 제외한다.

        C 상품처럼 월세금 대출이 별도 구조인 경우에도
        실제 적용된 보증금 대출 원금만 +2%p 스트레스한다.
        """

        base_total_monthly_cost = (
            to_float(
                monthly_cost_result.get(
                    "net_monthly_cost_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        base_loan_interest = (
            to_float(
                monthly_cost_result.get(
                    "loan_interest_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        applied = bool(
            finance.get(
                "applied"
            )
        )

        estimated_loan = (
            to_float(
                finance.get(
                    "estimated_loan_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        # 현재 비용 시나리오에 대출이 실제 적용되지 않았다면
        # 금리 스트레스도 적용하지 않는다.
        if (
            not applied
            or estimated_loan <= 0
        ):
            return {
                "interest_rate_increase_pct_point": (
                    interest_rate_increase_pct_point
                ),
                "base_loan_interest_manwon": round(
                    base_loan_interest,
                    2,
                ),
                "additional_monthly_interest_manwon": 0.0,
                "stressed_loan_interest_manwon": round(
                    base_loan_interest,
                    2,
                ),
                "stressed_total_monthly_cost_manwon": round(
                    base_total_monthly_cost,
                    2,
                ),
                "stress_scope": (
                    "no_applied_finance"
                ),
                "calculation_note": (
                    "현재 비용 시나리오에 실제 적용된 "
                    "주거대출이 없어 금리 스트레스를 "
                    "적용하지 않았습니다."
                ),
            }

        additional_interest = (
            estimated_loan
            * interest_rate_increase_pct_point
            / 100
            / 12
        )

        additional_interest = round(
            additional_interest,
            2,
        )

        stressed_loan_interest = round(
            base_loan_interest
            + additional_interest,
            2,
        )

        stressed_cost_result = (
            calculate_total_monthly_housing_cost_manwon(
                monthly_rent_manwon=monthly_rent,
                management_fee_manwon=management_fee,
                utilities_manwon=utilities,

                loan_principal_manwon=estimated_loan,

                # 기존 상품별 계산 이자에
                # 금리 상승분만 추가한다.
                precomputed_loan_interest_manwon=(
                    stressed_loan_interest
                ),

                own_cash_deposit_manwon=(
                    own_cash_deposit
                ),

                commute_cost_change_manwon=(
                    to_float(
                        monthly_cost_result.get(
                            "commute_cost_change_manwon"
                        ),
                        0.0,
                    )
                    or 0.0
                ),

                monthly_support_manwon=(
                    to_float(
                        monthly_cost_result.get(
                            "monthly_support_manwon"
                        ),
                        0.0,
                    )
                    or 0.0
                ),
            )
        )

        loan_estimate = finance.get(
            "loan_estimate",
            {},
        )

        if not isinstance(
            loan_estimate,
            Mapping,
        ):
            loan_estimate = {}

        has_monthly_rent_financing = (
            (
                to_float(
                    loan_estimate.get(
                        "estimated_monthly_rent_loan_total_manwon"
                    ),
                    0.0,
                )
                or 0.0
            )
            > 0
        )

        if has_monthly_rent_financing:
            stress_scope = (
                "applied_deposit_loan_only_"
                "monthly_rent_drawdown_excluded"
            )

            calculation_note = (
                "실제 비용 시나리오에 적용된 보증금 대출 원금에만 "
                f"금리 +{interest_rate_increase_pct_point:.1f}%p를 "
                "적용했습니다. 월세금 대출은 월별 실행액과 "
                "잔액이 달라질 수 있어 스트레스 계산에서 제외했습니다."
            )

        else:
            stress_scope = (
                "applied_deposit_loan"
            )

            calculation_note = (
                "현재 비용 시나리오에 적용된 보증금 대출 원금에 "
                f"금리 +{interest_rate_increase_pct_point:.1f}%p를 "
                "적용해 월 주거비를 다시 계산했습니다."
            )

        return {
            "interest_rate_increase_pct_point": (
                interest_rate_increase_pct_point
            ),

            "base_loan_interest_manwon": round(
                base_loan_interest,
                2,
            ),

            "additional_monthly_interest_manwon": (
                additional_interest
            ),

            "stressed_loan_interest_manwon": (
                stressed_loan_interest
            ),

            "stressed_total_monthly_cost_manwon": (
                stressed_cost_result[
                    "net_monthly_cost_manwon"
                ]
            ),

            "stress_scope": stress_scope,

            "calculation_note": (
                calculation_note
            ),
        }

    def _build_candidate(
        self,
        transaction_type: str,
        row: Mapping[str, Any],
        user: Mapping[str, Any],
        affordable_budget: float,
    ) -> dict[str, Any]:
        deposit = (
            to_float(
                row.get(
                    "deposit_median_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        if transaction_type == "monthly_rent":
            monthly_rent = (
                to_float(
                    row.get(
                        "monthly_rent_median_manwon"
                    ),
                    0.0,
                )
                or 0.0
            )
        else:
            monthly_rent = 0.0

        available_cash = (
            self._get_deposit_allocable_cash(
                user
            )
        )

        management_fee = (
            to_float(
                user.get(
                    "management_fee_assumption_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        utilities = (
            to_float(
                user.get(
                    "utilities_assumption_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        initial_gap = max(
            0.0,
            deposit - available_cash,
        )

        market_area_bucket = str(
            row.get(
                "market_area_bucket"
            )
        )

        representative_area = (
            self._representative_area_m2(
                market_area_bucket
            )
        )

        property_info = {
            "contract_type": transaction_type,
            "housing_type": row.get(
                "housing_type"
            ),
            "deposit_manwon": deposit,
            "monthly_rent_manwon": (
                monthly_rent
            ),
            "area_m2": representative_area,

            # 지역 추천 단계에서는 아직 실제 계약 전이므로
            # 계약금·임대인·중개 여부는 미확인으로 둔다.
            "contract_payment_ratio": None,
            "landlord_type": None,
            "is_brokered_contract": None,
        }

        policy_supports = (
            self._get_policy_support_matcher()
            .match_all(
                user=user,
                property_info=property_info,
            )
        )


        finance = self._select_finance_option(
            user=user,
            property_info=property_info,
            original_gap=initial_gap,
        )

        monthly_interest = (
            to_float(
                finance.get(
                    "monthly_interest_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        remaining_gap = (
            to_float(
                finance.get(
                    "remaining_gap_manwon"
                ),
                initial_gap,
            )
            or 0.0
        )

        estimated_loan = (
            to_float(
                finance.get(
                    "estimated_loan_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        own_cash_deposit = max(
            0.0,
            deposit - estimated_loan,
        )

        monthly_cost_result = (
            calculate_total_monthly_housing_cost_manwon(
                monthly_rent_manwon=monthly_rent,
                management_fee_manwon=management_fee,
                utilities_manwon=utilities,

                # 대출 자체 정보
                loan_principal_manwon=estimated_loan,

                # 상품별 이자는 FinanceMatcher가 계산한 값을 사용
                precomputed_loan_interest_manwon=(
                    monthly_interest
                ),

                # 기회비용은 전체 보증금이 아니라
                # 실제 자기자금 투입분만 계산
                own_cash_deposit_manwon=(
                    own_cash_deposit
                ),

                # 현재 MVP 미구현 값
                commute_cost_change_manwon=0.0,
                monthly_support_manwon=0.0,
            )
        )

        total_monthly_cost = (
            monthly_cost_result[
                "net_monthly_cost_manwon"
            ]
        )

        if affordable_budget > 0:
            affordability_ratio = (
                total_monthly_cost
                / affordable_budget
            )
        else:
            affordability_ratio = float(
                "inf"
            )

        affordability_score = (
            self._affordability_score(
                monthly_cost=total_monthly_cost,
                budget=affordable_budget,
            )
        )

        initial_funds_score = (
            self._initial_funds_score(
                remaining_gap=remaining_gap,
                deposit=deposit,
            )
        )

        (
            preference_score,
            district_preference_rank,
        ) = self._district_preference_score(
            district_name=row.get(
                "district_name"
            ),
            user=user,
        )

        confidence = str(
            row.get(
                "confidence",
                "very_low",
            )
        )

        reliability_score = (
            CONFIDENCE_SCORE.get(
                confidence,
                2.0,
            )
        )

        loan_burden_score = (
            self._loan_burden_score(
                loan_amount=estimated_loan,
                deposit=deposit,
            )
        )

        total_score = round(
            affordability_score
            + initial_funds_score
            + preference_score
            + reliability_score
            + loan_burden_score,
            2,
        )

        (
            judgement_code,
            judgement_label,
        ) = self._final_judgement(
            total_score=total_score,
            affordability_ratio=(
                affordability_ratio
            ),
            remaining_gap=remaining_gap,
        )

        stress_test = (
            self._calculate_finance_stress_test(
                finance=finance,
                monthly_cost_result=(
                    monthly_cost_result
                ),
                monthly_rent=monthly_rent,
                management_fee=management_fee,
                utilities=utilities,
                own_cash_deposit=(
                    own_cash_deposit
                ),
                interest_rate_increase_pct_point=2.0,
            )
        )

        future_simulation = (
            self._future_simulation(
                user=user,
                monthly_housing_cost=(
                    total_monthly_cost
                ),
            )
        )

        housing_type = str(
            row.get(
                "housing_type"
            )
        )

        district_name = str(
            row.get(
                "district_name"
            )
        )

        candidate_id = (
            f"{transaction_type}:"
            f"{row.get('district_code')}:"
            f"{housing_type}:"
            f"{market_area_bucket}:"
            f"{row.get('deposit_bucket', 'all')}"
        )

        if total_monthly_cost <= affordable_budget:
            difference = round(
                affordable_budget
                - total_monthly_cost,
                2,
            )

            affordability_text = (
                f"예상 총 월 주거비는 "
                f"{total_monthly_cost:.1f}만원으로, "
                f"권장 주거비 {affordable_budget:.1f}만원보다 "
                f"{difference:.1f}만원 낮습니다."
            )

        else:
            difference = round(
                total_monthly_cost
                - affordable_budget,
                2,
            )

            affordability_text = (
                f"예상 총 월 주거비는 "
                f"{total_monthly_cost:.1f}만원으로, "
                f"권장 주거비 {affordable_budget:.1f}만원을 "
                f"{difference:.1f}만원 초과합니다."
            )

        if initial_gap <= 0:
            initial_funds_text = (
                f"보증금 중앙값 {deposit:,.0f}만원을 "
                f"현재 보유 자금으로 마련할 수 있습니다."
            )

        elif remaining_gap <= 0:
            initial_funds_text = (
                f"보증금 중앙값 {deposit:,.0f}만원 중 "
                f"{initial_gap:,.0f}만원이 부족하지만, "
                f"금융상품 예상 적용 후 부족액은 없습니다."
            )

        else:
            initial_funds_text = (
                f"보증금 중앙값 {deposit:,.0f}만원 중 "
                f"금융상품 예상 적용 후에도 "
                f"{remaining_gap:,.0f}만원이 부족합니다."
            )

        if finance["applied"]:
            finance_text = (
                f"{finance['product_name']} "
                f"사전 매칭 결과를 적용하면 "
                f"예상 대출액은 "
                f"{estimated_loan:,.0f}만원, "
                f"예상 월 이자는 "
                f"{monthly_interest:.1f}만원입니다. "
                f"최종 승인 여부는 별도 심사가 필요합니다."
            )

        elif (
                finance.get(
                    "selection_reason"
                )
                == "optional_monthly_rent_financing_available"
        ):
            optional_amount = (
                    to_float(
                        finance.get(
                            "available_monthly_rent_financing_manwon"
                        ),
                        0.0,
                    )
                    or 0.0
            )

            optional_interest = (
                    to_float(
                        finance.get(
                            "estimated_monthly_interest_if_used_manwon"
                        ),
                        0.0,
                    )
                    or 0.0
            )

            finance_text = (
                f"현재 보증금은 보유 자금으로 마련 가능하지만, "
                f"{finance['product_name']}을 통해 "
                f"최대 약 {optional_amount:,.0f}만원의 "
                f"월세 금융을 이용할 수 있습니다. "
                f"이용 시 예상 월 이자는 최대 "
                f"{optional_interest:.1f}만원 수준이며, "
                f"현재 추천 비용 계산에는 적용하지 않았습니다."
            )

        elif initial_gap <= 0:
            finance_text = (
                "현재 보유 자금으로 보증금 마련이 가능해 "
                "금융상품을 적용하지 않았습니다."
            )

        else:
            finance_text = (
                "현재 입력 조건에서 적용 가능한 금융상품을 "
                "확정하지 못해 추가 확인이 필요합니다."
            )

        return {
            "candidate_id": candidate_id,
            "transaction_type": (
                transaction_type
            ),
            "transaction_type_label": (
                "월세"
                if transaction_type
                == "monthly_rent"
                else "전세"
            ),
            "district_code": str(
                row.get(
                    "district_code"
                )
            ),
            "district_name": district_name,
            "district_preference_rank": (
                district_preference_rank
            ),
            "housing_type": housing_type,
            "housing_type_label": (
                HOUSING_TYPE_LABELS.get(
                    housing_type,
                    housing_type,
                )
            ),
            "front_area_bucket": str(
                row.get(
                    "front_area_bucket"
                )
            ),
            "market_area_bucket": (
                market_area_bucket
            ),
            "area_label": (
                MARKET_AREA_LABELS.get(
                    market_area_bucket,
                    market_area_bucket,
                )
            ),
            "representative_area_upper_m2": (
                representative_area
            ),
            "deposit_bucket": row.get(
                "deposit_bucket"
            ),
            "deposit_bucket_label": row.get(
                "deposit_bucket_label"
            ),
            "market_price": {
                "deposit_q25_manwon": (
                    round_money(
                        row.get(
                            "deposit_q25_manwon"
                        )
                    )
                ),
                "deposit_median_manwon": (
                    round(
                        deposit,
                        2,
                    )
                ),
                "deposit_q75_manwon": (
                    round_money(
                        row.get(
                            "deposit_q75_manwon"
                        )
                    )
                ),
                "monthly_rent_q25_manwon": (
                    round_money(
                        row.get(
                            "monthly_rent_q25_manwon"
                        )
                    )
                ),
                "monthly_rent_median_manwon": (
                    round(
                        monthly_rent,
                        2,
                    )
                ),
                "monthly_rent_q75_manwon": (
                    round_money(
                        row.get(
                            "monthly_rent_q75_manwon"
                        )
                    )
                ),
                "contract_count": int(
                    to_float(
                        row.get(
                            "contract_count"
                        ),
                        0,
                    )
                    or 0
                ),
                "confidence": confidence,
                "contract_scope": row.get(
                    "contract_scope"
                ),
                "data_start_date": row.get(
                    "data_start_date"
                ),
                "data_end_date": row.get(
                    "data_end_date"
                ),
            },
            "initial_funds": {
                "available_cash_manwon": round(
                    available_cash,
                    2,
                ),
                "deposit_gap_before_loan_manwon": round(
                    initial_gap,
                    2,
                ),
                "estimated_loan_manwon": round(
                    estimated_loan,
                    2,
                ),
                "remaining_gap_after_loan_manwon": round(
                    remaining_gap,
                    2,
                ),
            },
            "monthly_cost": {
                "monthly_rent_manwon": round(
                    monthly_rent,
                    2,
                ),
                "management_fee_assumption_manwon": round(
                    management_fee,
                    2,
                ),
                "utilities_assumption_manwon": round(
                    utilities,
                    2,
                ),
                "loan_interest_manwon": round(
                    monthly_interest,
                    2,
                ),
                "total_monthly_housing_cost_manwon": round(
                    total_monthly_cost,
                    2,
                ),
                "own_cash_deposit_manwon": round(
                    own_cash_deposit,
                    2,
                ),
                "deposit_opportunity_cost_manwon": (
                    monthly_cost_result[
                        "deposit_opportunity_cost_manwon"
                    ]
                ),
                "commute_cost_change_manwon": (
                    monthly_cost_result[
                        "commute_cost_change_manwon"
                    ]
                ),
                "monthly_support_manwon": (
                    monthly_cost_result[
                        "monthly_support_manwon"
                    ]
                ),
                "gross_monthly_housing_cost_manwon": (
                    monthly_cost_result[
                        "gross_monthly_cost_manwon"
                    ]
                ),
                "affordable_monthly_housing_cost_manwon": round(
                    affordable_budget,
                    2,
                ),
                "affordability_ratio": round(
                    affordability_ratio,
                    4,
                ),
            },

            "policy_supports": (
                policy_supports
            ),

            "finance": finance,

            "stress_test": (
                stress_test
            ),

            "future_simulation": (
                future_simulation
            ),
            "score": {
                "affordability": (
                    affordability_score
                ),
                "initial_funds": (
                    initial_funds_score
                ),
                "preference": (
                    preference_score
                ),
                "data_reliability": (
                    reliability_score
                ),
                "loan_burden": (
                    loan_burden_score
                ),
                "total": total_score,
            },
            "judgement": {
                "code": judgement_code,
                "label": judgement_label,
            },
            "explanations": {
                "affordability": (
                    affordability_text
                ),
                "district_preference": (
                    (
                        f"{district_name}은 "
                        f"사용자의 {district_preference_rank}순위 "
                        f"선호 지역입니다."
                    )
                    if district_preference_rank
                       is not None
                    else (
                        "선호 지역 순위가 지정되지 않았거나 "
                        "해당 후보가 선호 지역 외 지역입니다."
                    )
                ),
                "market_basis": (
                    f"{district_name} "
                    f"{HOUSING_TYPE_LABELS.get(housing_type, housing_type)} "
                    f"{MARKET_AREA_LABELS.get(market_area_bucket, market_area_bucket)} "
                    f"최근 실거래 중앙값을 기준으로 계산했습니다."
                ),
                "initial_funds": (
                    initial_funds_text
                ),
                "finance": finance_text,
                "stress_test": (
                    stress_test[
                        "calculation_note"
                    ]
                ),
                "final_judgement": (
                    judgement_label
                ),
            },
        }

    @staticmethod
    def _diversify_candidates(
        candidates: list[dict[str, Any]],
        top_n: int,
    ) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        seen_keys: set[tuple[str, str, str]] = set()

        for candidate in candidates:
            diversity_key = (
                candidate[
                    "transaction_type"
                ],
                candidate[
                    "district_name"
                ],
                candidate[
                    "housing_type"
                ],
            )

            if diversity_key in seen_keys:
                continue

            seen_keys.add(diversity_key)
            selected.append(candidate)

            if len(selected) >= top_n:
                break

        if len(selected) < top_n:
            selected_ids = {
                candidate["candidate_id"]
                for candidate in selected
            }

            for candidate in candidates:
                if (
                    candidate["candidate_id"]
                    in selected_ids
                ):
                    continue

                selected.append(candidate)

                if len(selected) >= top_n:
                    break

        return selected

    def recommend(
        self,
        user: Mapping[str, Any],
        top_n: int = 5,
    ) -> dict[str, Any]:
        contract_preference = (
            normalize_contract_preference(
                user.get(
                    "contract_preference",
                    "both",
                )
            )
        )

        contract_types = (
            self._resolve_contract_types(
                contract_preference
            )
        )

        (
            affordable_budget,
            budget_source,
        ) = self._get_affordable_budget(user)

        all_candidates: list[
            dict[str, Any]
        ] = []

        candidate_counts = {}

        for transaction_type in contract_types:
            market_candidates = (
                self._get_market_candidates(
                    transaction_type=(
                        transaction_type
                    ),
                    user=user,
                    affordable_budget=(
                        affordable_budget
                    ),
                )
            )

            candidate_counts[
                transaction_type
            ] = len(market_candidates)

            for row in market_candidates.to_dict(
                orient="records"
            ):
                all_candidates.append(
                    self._build_candidate(
                        transaction_type=(
                            transaction_type
                        ),
                        row=row,
                        user=user,
                        affordable_budget=(
                            affordable_budget
                        ),
                    )
                )

        judgement_rank = {
            "recommended": 0,
            "conditionally_recommended": 1,
            "consider_other_area": 2,
            "budget_exceeded": 3,
        }

        all_candidates.sort(
            key=lambda candidate: (
                judgement_rank.get(
                    candidate[
                        "judgement"
                    ]["code"],
                    99,
                ),
                -candidate["score"]["total"],
                candidate[
                    "monthly_cost"
                ][
                    "total_monthly_housing_cost_manwon"
                ],
                candidate[
                    "initial_funds"
                ][
                    "remaining_gap_after_loan_manwon"
                ],
            )
        )

        selected_candidates = (
            self._diversify_candidates(
                candidates=all_candidates,
                top_n=top_n,
            )
        )

        return {
            "engine_version": (
                "housing_plan_recommender_v1"
            ),
            "recommendation_basis": (
                "regional_market_summary_and_rule_based_finance_matching"
            ),
            "input_summary": {
                "contract_preference": (
                    contract_preference
                ),
                "preferred_housing_types": (
                    normalize_housing_types(
                        user.get(
                            "preferred_housing_types"
                        )
                    )
                ),
                "minimum_area_bucket": (
                    user.get(
                        "minimum_area_bucket",
                        "any",
                    )
                ),
                "housing_funds_manwon": (
                    round_money(
                        user.get(
                            "housing_funds_manwon"
                        )
                    )
                ),
                "loan_preference": (
                    user.get(
                        "loan_preference"
                    )
                ),
                "preferred_district_names": (
                    normalize_preferred_district_names(
                        user.get(
                            "preferred_district_names"
                        )
                    )
                ),
                "allowed_district_names": (
                    user.get(
                        "allowed_district_names"
                    )
                ),
            },
            "affordable_budget": {
                "amount_manwon": round(
                    affordable_budget,
                    2,
                ),
                "source": budget_source,
            },
            "candidate_counts_before_full_scoring": (
                candidate_counts
            ),
            "recommendation_count": len(
                selected_candidates
            ),
            "recommendations": (
                selected_candidates
            ),
            "limitations": [
                (
                    "통근시간은 아직 실제 교통 API와 "
                    "연결되지 않았습니다."
                ),
                (
                    "관리비와 공과금은 사용자 또는 팀이 "
                    "입력한 가정값을 사용합니다."
                ),
                (
                    "금융상품 결과는 실제 승인 결과가 아닌 "
                    "일반 조건 기반 사전 매칭입니다."
                ),
                (
                    "실시간 매물이 아닌 최근 실거래 "
                    "가격대를 추천합니다."
                ),
            ],
        }
