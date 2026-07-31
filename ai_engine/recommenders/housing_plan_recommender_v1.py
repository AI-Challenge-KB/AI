from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from ai_engine.finance.finance_matcher_v1 import (
    FinanceMatcherV1,
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

    1. 초기자금 부족분을 전액 충당하는 상품 우선
    2. 전액 충당 상품끼리는 낮은 금리 우선
    3. 금리가 같으면 월 이자가 낮은 상품 우선
    4. 전액 충당 상품이 없으면 남은 부족액이 작은 상품 우선
    """
    remaining_gap = max(
        0.0,
        _safe_float(
            option.get("remaining_gap_manwon"),
            default=0.0,
        ),
    )

    annual_rate = (
        _get_finance_option_annual_rate_pct(option)
    )

    monthly_interest = _safe_float(
        option.get("monthly_interest_manwon")
    )

    product_id = str(
        option.get("product_id") or ""
    )

    fully_funded = (
        remaining_gap
        <= FULL_FUNDING_GAP_TOLERANCE_MANWON
    )

    if fully_funded:
        # 보증금 부족분을 모두 충당할 수 있다면
        # 낮은 금리부터 선택한다.
        return (
            0,
            annual_rate,
            monthly_interest,
            product_id,
        )

    # 전액 충당 가능한 상품이 없다면
    # 부족액을 가장 많이 줄여주는 상품을 선택한다.
    return (
        1,
        remaining_gap,
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

    @staticmethod
    def _get_affordable_budget(
        user: Mapping[str, Any],
    ) -> tuple[float, str]:
        explicit_budget = to_float(
            user.get(
                "affordable_monthly_housing_cost_manwon"
            )
        )

        if explicit_budget is not None:
            return (
                max(explicit_budget, 0.0),
                "provided_by_affordability_calculator",
            )

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

        if monthly_income is None:
            raise ValueError(
                "affordable_monthly_housing_cost_manwon 또는 "
                "월 소득 정보가 필요합니다."
            )

        residual_budget = max(
            0.0,
            monthly_income
            - living_expense
            - debt_payment
            - target_savings,
        )

        income_ratio_budget = max(
            0.0,
            monthly_income * 0.30,
        )

        return (
            round(
                min(
                    residual_budget,
                    income_ratio_budget,
                ),
                2,
            ),
            "fallback_min_of_residual_and_30_percent",
        )

    @staticmethod
    def _filter_allowed_districts(
        dataframe: pd.DataFrame,
        user: Mapping[str, Any],
    ) -> pd.DataFrame:
        allowed_districts = user.get(
            "allowed_district_names"
        )

        if is_missing(allowed_districts):
            return dataframe

        if isinstance(allowed_districts, str):
            allowed_districts = [
                allowed_districts
            ]

        return dataframe[
            dataframe["district_name"].isin(
                allowed_districts
            )
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
            to_float(
                user.get(
                    "housing_funds_manwon"
                ),
                0.0,
            )
            or 0.0
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

        if transaction_type == "monthly_rent":
            candidates[
                "_rough_monthly_cost"
            ] = (
                candidates[
                    "monthly_rent_median_manwon"
                ]
                + management_fee
                + utilities
            )

        else:
            candidates[
                "_rough_monthly_cost"
            ] = (
                management_fee
                + utilities
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

        candidates["_rough_rank"] = (
            candidates[
                "_rough_budget_distance"
            ]
            + candidates[
                "_rough_deposit_gap_ratio"
            ]
            * 0.5
            + confidence_penalty
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

        upper_interest = to_float(
            loan_estimate.get(
                "estimated_monthly_interest_upper_manwon"
            )
        )

        if upper_interest is not None:
            return max(
                upper_interest,
                0.0,
            )

        return 0.0

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

    def _select_finance_option(
        self,
        user: Mapping[str, Any],
        property_info: Mapping[str, Any],
        original_gap: float,
    ) -> dict[str, Any]:
        loan_preference = str(
            user.get(
                "loan_preference",
                "available",
            )
        )

        if (
            original_gap <= 0
            or loan_preference == "no_loan"
            or loan_preference == "대출 없이 추천"
        ):
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
            }

        matches = self.finance_matcher.match_all(
            user=user,
            property_info=property_info,
        )

        eligible_estimates = []

        for match in matches:
            if match["match_status"] == "ineligible":
                continue

            estimate = match.get(
                "loan_estimate",
                {},
            )

            if (
                estimate.get(
                    "calculation_status"
                )
                != "estimated"
            ):
                continue

            estimated_loan = (
                self._extract_deposit_loan(
                    estimate
                )
            )

            if estimated_loan <= 0:
                continue

            monthly_interest = (
                self._extract_monthly_interest(
                    estimate
                )
            )

            remaining_gap = (
                self._extract_remaining_gap(
                    estimate,
                    original_gap,
                )
            )

            eligible_estimates.append(
                {
                    "product_id": match[
                        "product_id"
                    ],
                    "product_name": match[
                        "product_name"
                    ],
                    "match_status": match[
                        "match_status"
                    ],
                    "estimated_loan_manwon": (
                        estimated_loan
                    ),
                    "monthly_interest_manwon": (
                        monthly_interest
                    ),
                    "remaining_gap_manwon": (
                        remaining_gap
                    ),
                    "missing_fields": match[
                        "missing_fields"
                    ],
                    "loan_estimate": estimate,
                }
            )

        if not eligible_estimates:
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
                "all_matches": matches,
            }

        eligible_estimates.sort(
            key=_finance_option_sort_key
        )

        selected = eligible_estimates[0]

        return {
            "applied": True,
            **selected,
            "all_matches": matches,
        }

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
            to_float(
                user.get(
                    "housing_funds_manwon"
                ),
                0.0,
            )
            or 0.0
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

        total_monthly_cost = (
            monthly_rent
            + management_fee
            + utilities
            + monthly_interest
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

        preference_score = 10.0

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

        stress_rate_increase_pct = 2.0

        stress_additional_interest = round(
            estimated_loan
            * stress_rate_increase_pct
            / 100
            / 12,
            2,
        )

        stress_monthly_cost = round(
            total_monthly_cost
            + stress_additional_interest,
            2,
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
                f"{finance['product_name']} 사전 매칭 결과를 적용하면 "
                f"예상 대출액은 {estimated_loan:,.0f}만원, "
                f"예상 월 이자는 {monthly_interest:.1f}만원입니다. "
                f"최종 승인 여부는 별도 심사가 필요합니다."
            )

        elif initial_gap <= 0:
            finance_text = (
                "현재 보유 자금으로 보증금 마련이 가능해 "
                "대출을 적용하지 않았습니다."
            )

        else:
            finance_text = (
                "현재 입력 조건에서 적용 가능한 대출을 확정하지 못해 "
                "금융상품 추가 확인이 필요합니다."
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
                "affordable_monthly_housing_cost_manwon": round(
                    affordable_budget,
                    2,
                ),
                "affordability_ratio": round(
                    affordability_ratio,
                    4,
                ),
            },
            "finance": finance,
            "stress_test": {
                "interest_rate_increase_pct_point": (
                    stress_rate_increase_pct
                ),
                "additional_monthly_interest_manwon": (
                    stress_additional_interest
                ),
                "stressed_total_monthly_cost_manwon": (
                    stress_monthly_cost
                ),
            },
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
                    f"적용 대출금리가 2%p 상승하면 "
                    f"예상 월 주거비가 "
                    f"{stress_additional_interest:.1f}만원 증가합니다."
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
