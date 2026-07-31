from __future__ import annotations

import json
import math
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FINANCE_DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "finance"
)

LOAN_PRODUCT_PATH = (
    FINANCE_DATA_DIR
    / "loan_product_master.csv"
)

LOAN_RULE_PATH = (
    FINANCE_DATA_DIR
    / "loan_eligibility_rules.csv"
)


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

    if isinstance(
        value,
        (
            list,
            tuple,
            dict,
            set,
        ),
    ):
        return False

    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def parse_json_cell(
    value: Any,
    default: Any,
) -> Any:
    if is_missing(value):
        return default

    if isinstance(
        value,
        (
            list,
            dict,
            bool,
            int,
            float,
        ),
    ):
        return value

    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return default


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


def calculate_age(
    birth_date: str | date | datetime,
    evaluation_date: date | None = None,
) -> int:
    evaluation_date = evaluation_date or date.today()

    if isinstance(birth_date, datetime):
        birth = birth_date.date()

    elif isinstance(birth_date, date):
        birth = birth_date

    else:
        birth = datetime.strptime(
            str(birth_date),
            "%Y-%m-%d",
        ).date()

    age = evaluation_date.year - birth.year

    if (
        evaluation_date.month,
        evaluation_date.day,
    ) < (
        birth.month,
        birth.day,
    ):
        age -= 1

    return age


def normalize_contract_type(
    value: Any,
) -> str | None:
    if is_missing(value):
        return None

    normalized = (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
    )

    aliases = {
        "jeonse": "jeonse",
        "전세": "jeonse",
        "monthly_rent": "monthly_rent_with_deposit",
        "monthly_rent_with_deposit": (
            "monthly_rent_with_deposit"
        ),
        "월세": "monthly_rent_with_deposit",
        "보증부월세": "monthly_rent_with_deposit",
    }

    return aliases.get(
        normalized,
        normalized,
    )


def normalize_housing_type(
    value: Any,
) -> str | None:
    if is_missing(value):
        return None

    normalized = (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
    )

    aliases = {
        "아파트": "apartment",
        "오피스텔": "officetel",
        "연립·다세대": "row_house",
        "연립다세대": "row_house",
        "연립_다세대": "row_house",
        "단독·다가구": "single_multi_house",
        "단독다가구": "single_multi_house",
        "단독_다가구": "single_multi_house",
    }

    return aliases.get(
        normalized,
        normalized,
    )


class FinanceMatcherV1:
    """
    금융상품 사전 매칭 및 예상 대출액 계산 엔진.

    반환 상태:
    - likely_eligible:
      현재 입력된 조건에서는 주요 조건을 통과함
    - needs_more_info:
      판단에 필요한 입력이 부족함
    - ineligible:
      명시적인 상품 조건을 충족하지 못함

    실제 금융기관 승인 결과를 의미하지 않는다.
    """

    def __init__(
        self,
        loan_product_path: Path = LOAN_PRODUCT_PATH,
        loan_rule_path: Path = LOAN_RULE_PATH,
    ) -> None:
        if not loan_product_path.exists():
            raise FileNotFoundError(
                "loan_product_master.csv가 없습니다.\n"
                f"예상 경로: {loan_product_path}"
            )

        if not loan_rule_path.exists():
            raise FileNotFoundError(
                "loan_eligibility_rules.csv가 없습니다.\n"
                f"예상 경로: {loan_rule_path}"
            )

        self.products = pd.read_csv(
            loan_product_path,
            encoding="utf-8-sig",
        )

        self.rules = pd.read_csv(
            loan_rule_path,
            encoding="utf-8-sig",
        )

        self._validate_master_data()

    def _validate_master_data(self) -> None:
        required_product_columns = {
            "product_id",
            "product_name",
            "supported_contract_types_json",
            "eligible_housing_types_json",
            "loan_formula_key",
        }

        missing_product_columns = (
            required_product_columns
            - set(self.products.columns)
        )

        if missing_product_columns:
            raise ValueError(
                "loan_product_master.csv 필수 컬럼 누락: "
                f"{sorted(missing_product_columns)}"
            )

        required_rule_columns = {
            "rule_id",
            "product_id",
            "field_name",
            "operator",
            "threshold_json",
            "applies_when_json",
            "missing_behavior",
            "description",
        }

        missing_rule_columns = (
            required_rule_columns
            - set(self.rules.columns)
        )

        if missing_rule_columns:
            raise ValueError(
                "loan_eligibility_rules.csv 필수 컬럼 누락: "
                f"{sorted(missing_rule_columns)}"
            )

        if not self.products["product_id"].is_unique:
            raise ValueError(
                "금융상품 product_id가 중복되어 있습니다."
            )

        if not self.rules["rule_id"].is_unique:
            raise ValueError(
                "금융상품 rule_id가 중복되어 있습니다."
            )

    def _build_context(
        self,
        user: Mapping[str, Any],
        property_info: Mapping[str, Any],
    ) -> dict[str, Any]:
        context = dict(user)

        context.update(
            {
                "property_contract_type": (
                    normalize_contract_type(
                        property_info.get(
                            "contract_type"
                        )
                    )
                ),
                "property_housing_type": (
                    normalize_housing_type(
                        property_info.get(
                            "housing_type"
                        )
                    )
                ),
                "property_deposit_manwon": (
                    property_info.get(
                        "deposit_manwon"
                    )
                ),
                "property_monthly_rent_manwon": (
                    property_info.get(
                        "monthly_rent_manwon"
                    )
                ),
                "property_area_m2": (
                    property_info.get(
                        "area_m2"
                    )
                ),
                "contract_payment_ratio": (
                    property_info.get(
                        "contract_payment_ratio"
                    )
                ),
                "landlord_type": (
                    property_info.get(
                        "landlord_type"
                    )
                ),
                "is_brokered_contract": (
                    property_info.get(
                        "is_brokered_contract"
                    )
                ),
            }
        )

        if is_missing(context.get("age")):
            birth_date = context.get("birth_date")

            if not is_missing(birth_date):
                evaluation_date_raw = context.get(
                    "evaluation_date"
                )

                evaluation_date = None

                if not is_missing(
                    evaluation_date_raw
                ):
                    evaluation_date = datetime.strptime(
                        str(evaluation_date_raw),
                        "%Y-%m-%d",
                    ).date()

                context["age"] = calculate_age(
                    birth_date=birth_date,
                    evaluation_date=evaluation_date,
                )

        if is_missing(
            context.get(
                "household_annual_income_manwon"
            )
        ):
            annual_income = context.get(
                "annual_income_manwon"
            )

            monthly_income = context.get(
                "monthly_income_manwon"
            )

            if not is_missing(annual_income):
                context[
                    "household_annual_income_manwon"
                ] = annual_income

            elif not is_missing(monthly_income):
                context[
                    "household_annual_income_manwon"
                ] = (
                    float(monthly_income)
                    * 12
                )

        if is_missing(
            context.get(
                "available_cash_manwon"
            )
        ):
            context[
                "available_cash_manwon"
            ] = context.get(
                "housing_funds_manwon"
            )

        return context

    @staticmethod
    def _split_condition_key(
        key: str,
    ) -> tuple[str, str]:
        suffix_operators = [
            ("_lte", "lte"),
            ("_gte", "gte"),
            ("_lt", "lt"),
            ("_gt", "gt"),
        ]

        for suffix, operator in suffix_operators:
            if key.endswith(suffix):
                return (
                    key[: -len(suffix)],
                    operator,
                )

        return key, "eq"

    @staticmethod
    def _compare(
        value: Any,
        operator: str,
        threshold: Any,
    ) -> bool:
        if operator == "eq":
            return value == threshold

        if operator == "neq":
            return value != threshold

        if operator == "in":
            return value in threshold

        if operator == "not_in":
            return value not in threshold

        if operator in {
            "lt",
            "lte",
            "gt",
            "gte",
        }:
            numeric_value = to_float(value)
            numeric_threshold = to_float(
                threshold
            )

            if (
                numeric_value is None
                or numeric_threshold is None
            ):
                return False

            if operator == "lt":
                return (
                    numeric_value
                    < numeric_threshold
                )

            if operator == "lte":
                return (
                    numeric_value
                    <= numeric_threshold
                )

            if operator == "gt":
                return (
                    numeric_value
                    > numeric_threshold
                )

            return (
                numeric_value
                >= numeric_threshold
            )

        raise ValueError(
            f"지원하지 않는 연산자: {operator}"
        )

    def _check_applies_when(
        self,
        condition: dict[str, Any],
        context: Mapping[str, Any],
    ) -> tuple[
        bool | None,
        list[str],
    ]:
        if not condition:
            return True, []

        missing_fields: list[str] = []

        for key, expected in condition.items():
            field_name, operator = (
                self._split_condition_key(key)
            )

            value = context.get(field_name)

            if is_missing(value):
                missing_fields.append(
                    field_name
                )
                continue

            if not self._compare(
                value=value,
                operator=operator,
                threshold=expected,
            ):
                return False, []

        if missing_fields:
            return None, missing_fields

        return True, []

    def _evaluate_rule(
        self,
        rule: Mapping[str, Any],
        context: Mapping[str, Any],
    ) -> dict[str, Any]:
        applies_when = parse_json_cell(
            rule.get(
                "applies_when_json"
            ),
            {},
        )

        (
            applies,
            applicability_missing,
        ) = self._check_applies_when(
            condition=applies_when,
            context=context,
        )

        base_result = {
            "rule_id": rule["rule_id"],
            "field_name": rule["field_name"],
            "description": rule["description"],
            "evaluation_stage": rule.get(
                "evaluation_stage"
            ),
        }

        if applies is False:
            return {
                **base_result,
                "status": "skipped",
                "actual_value": None,
                "required_value": None,
                "missing_fields": [],
            }

        if applies is None:
            return {
                **base_result,
                "status": "needs_more_info",
                "actual_value": None,
                "required_value": None,
                "missing_fields": (
                    applicability_missing
                ),
            }

        field_name = str(
            rule["field_name"]
        )

        value = context.get(
            field_name
        )

        threshold = parse_json_cell(
            rule.get(
                "threshold_json"
            ),
            None,
        )

        if is_missing(value):
            return {
                **base_result,
                "status": "needs_more_info",
                "actual_value": None,
                "required_value": threshold,
                "missing_fields": [
                    field_name
                ],
            }

        passed = self._compare(
            value=value,
            operator=str(
                rule["operator"]
            ),
            threshold=threshold,
        )

        return {
            **base_result,
            "status": (
                "passed"
                if passed
                else "failed"
            ),
            "actual_value": value,
            "required_value": threshold,
            "missing_fields": [],
        }

    def _check_product_compatibility(
        self,
        product: Mapping[str, Any],
        context: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        supported_contract_types = (
            parse_json_cell(
                product.get(
                    "supported_contract_types_json"
                ),
                [],
            )
        )

        contract_type = context.get(
            "property_contract_type"
        )

        if is_missing(contract_type):
            results.append(
                {
                    "rule_id": (
                        "compatibility_contract_type"
                    ),
                    "field_name": (
                        "property_contract_type"
                    ),
                    "description": (
                        "상품이 지원하는 계약 형태 확인"
                    ),
                    "evaluation_stage": (
                        "property_check"
                    ),
                    "status": "needs_more_info",
                    "actual_value": None,
                    "required_value": (
                        supported_contract_types
                    ),
                    "missing_fields": [
                        "property_contract_type"
                    ],
                }
            )

        elif (
            contract_type
            not in supported_contract_types
        ):
            results.append(
                {
                    "rule_id": (
                        "compatibility_contract_type"
                    ),
                    "field_name": (
                        "property_contract_type"
                    ),
                    "description": (
                        "해당 계약 형태를 지원하지 않음"
                    ),
                    "evaluation_stage": (
                        "property_check"
                    ),
                    "status": "failed",
                    "actual_value": contract_type,
                    "required_value": (
                        supported_contract_types
                    ),
                    "missing_fields": [],
                }
            )

        else:
            results.append(
                {
                    "rule_id": (
                        "compatibility_contract_type"
                    ),
                    "field_name": (
                        "property_contract_type"
                    ),
                    "description": (
                        "상품 지원 계약 형태"
                    ),
                    "evaluation_stage": (
                        "property_check"
                    ),
                    "status": "passed",
                    "actual_value": contract_type,
                    "required_value": (
                        supported_contract_types
                    ),
                    "missing_fields": [],
                }
            )

        eligible_housing_types = (
            parse_json_cell(
                product.get(
                    "eligible_housing_types_json"
                ),
                [],
            )
        )

        housing_type = context.get(
            "property_housing_type"
        )

        if is_missing(housing_type):
            results.append(
                {
                    "rule_id": (
                        "compatibility_housing_type"
                    ),
                    "field_name": (
                        "property_housing_type"
                    ),
                    "description": (
                        "상품 대상 주택 유형 확인"
                    ),
                    "evaluation_stage": (
                        "property_check"
                    ),
                    "status": "needs_more_info",
                    "actual_value": None,
                    "required_value": (
                        eligible_housing_types
                    ),
                    "missing_fields": [
                        "property_housing_type"
                    ],
                }
            )

        elif (
            housing_type
            not in eligible_housing_types
        ):
            results.append(
                {
                    "rule_id": (
                        "compatibility_housing_type"
                    ),
                    "field_name": (
                        "property_housing_type"
                    ),
                    "description": (
                        "해당 주택 유형은 상품 대상이 아님"
                    ),
                    "evaluation_stage": (
                        "property_check"
                    ),
                    "status": "failed",
                    "actual_value": housing_type,
                    "required_value": (
                        eligible_housing_types
                    ),
                    "missing_fields": [],
                }
            )

        else:
            results.append(
                {
                    "rule_id": (
                        "compatibility_housing_type"
                    ),
                    "field_name": (
                        "property_housing_type"
                    ),
                    "description": (
                        "상품 대상 주택 유형"
                    ),
                    "evaluation_stage": (
                        "property_check"
                    ),
                    "status": "passed",
                    "actual_value": housing_type,
                    "required_value": (
                        eligible_housing_types
                    ),
                    "missing_fields": [],
                }
            )

        return results

    @staticmethod
    def _income_tier_rate(
        annual_income_manwon: float | None,
    ) -> tuple[float, str]:
        if annual_income_manwon is None:
            return (
                2.90,
                "소득 정보 부족으로 대표금리 2.90% 적용",
            )

        if annual_income_manwon <= 2000:
            return (
                2.20,
                "연소득 2천만원 이하 기준",
            )

        if annual_income_manwon <= 4000:
            return (
                2.50,
                "연소득 4천만원 이하 기준",
            )

        return (
            2.90,
            "일반 청년 연소득 구간 기준",
        )

    @staticmethod
    def _monthly_interest_manwon(
        principal_manwon: float,
        annual_rate_pct: float,
    ) -> float:
        return round(
            principal_manwon
            * annual_rate_pct
            / 100
            / 12,
            2,
        )

    def _estimate_kb_youth_custom(
        self,
        context: Mapping[str, Any],
        product: Mapping[str, Any],
    ) -> dict[str, Any]:
        deposit = to_float(
            context.get(
                "property_deposit_manwon"
            )
        )

        available_cash = to_float(
            context.get(
                "available_cash_manwon"
            )
        )

        if deposit is None or available_cash is None:
            missing = []

            if deposit is None:
                missing.append(
                    "property_deposit_manwon"
                )

            if available_cash is None:
                missing.append(
                    "available_cash_manwon"
                )

            return {
                "calculation_status": (
                    "needs_more_info"
                ),
                "missing_fields": missing,
            }

        deposit_gap = max(
            0.0,
            deposit - available_cash,
        )

        product_cap = (
            to_float(
                product.get(
                    "max_loan_manwon"
                ),
                20000,
            )
            or 20000
        )

        ratio = (
            to_float(
                product.get(
                    "max_loan_ratio"
                ),
                0.90,
            )
            or 0.90
        )

        property_based_limit = (
            deposit
            * ratio
        )

        estimated_loan = max(
            0.0,
            min(
                deposit_gap,
                product_cap,
                property_based_limit,
            ),
        )

        rate = (
            to_float(
                product.get(
                    "representative_rate_pct"
                ),
                3.80,
            )
            or 3.80
        )

        return {
            "calculation_status": "estimated",
            "deposit_manwon": round(
                deposit,
                2,
            ),
            "available_cash_manwon": round(
                available_cash,
                2,
            ),
            "deposit_gap_before_loan_manwon": round(
                deposit_gap,
                2,
            ),
            "estimated_deposit_loan_manwon": round(
                estimated_loan,
                2,
            ),
            "remaining_deposit_gap_manwon": round(
                max(
                    0.0,
                    deposit_gap
                    - estimated_loan,
                ),
                2,
            ),
            "applied_annual_rate_pct": rate,
            "estimated_monthly_interest_manwon": (
                self._monthly_interest_manwon(
                    estimated_loan,
                    rate,
                )
            ),
            "calculation_basis": (
                "min(보증금 부족액, 보증금의 90%, 2억원)"
            ),
            "disclaimer": (
                "HF 보증 가능 금액과 은행 심사에 따라 "
                "실제 한도와 금리가 달라질 수 있음"
            ),
        }

    def _estimate_butimok_jeonse(
        self,
        context: Mapping[str, Any],
    ) -> dict[str, Any]:
        deposit = to_float(
            context.get(
                "property_deposit_manwon"
            )
        )

        available_cash = to_float(
            context.get(
                "available_cash_manwon"
            )
        )

        if deposit is None or available_cash is None:
            missing = []

            if deposit is None:
                missing.append(
                    "property_deposit_manwon"
                )

            if available_cash is None:
                missing.append(
                    "available_cash_manwon"
                )

            return {
                "calculation_status": (
                    "needs_more_info"
                ),
                "missing_fields": missing,
            }

        age = to_float(
            context.get("age")
        )

        is_single = context.get(
            "is_single_household_head"
        )

        cap_note = (
            "일반 한도 1억5천만원 적용"
        )

        max_loan = 15000.0

        if (
            age is not None
            and age < 25
            and is_single is True
        ):
            max_loan = 12000.0
            cap_note = (
                "만 25세 미만 단독세대주 "
                "한도 1억2천만원 적용"
            )

        elif (
            age is not None
            and age < 25
            and is_missing(is_single)
        ):
            max_loan = 12000.0
            cap_note = (
                "단독세대주 여부 미입력으로 "
                "보수적으로 1억2천만원 적용"
            )

        deposit_gap = max(
            0.0,
            deposit - available_cash,
        )

        estimated_loan = max(
            0.0,
            min(
                deposit_gap,
                deposit * 0.80,
                max_loan,
            ),
        )

        annual_income = to_float(
            context.get(
                "household_annual_income_manwon"
            )
        )

        rate, rate_note = (
            self._income_tier_rate(
                annual_income
            )
        )

        return {
            "calculation_status": "estimated",
            "deposit_manwon": round(
                deposit,
                2,
            ),
            "available_cash_manwon": round(
                available_cash,
                2,
            ),
            "deposit_gap_before_loan_manwon": round(
                deposit_gap,
                2,
            ),
            "estimated_deposit_loan_manwon": round(
                estimated_loan,
                2,
            ),
            "remaining_deposit_gap_manwon": round(
                max(
                    0.0,
                    deposit_gap
                    - estimated_loan,
                ),
                2,
            ),
            "applied_annual_rate_pct": rate,
            "estimated_monthly_interest_manwon": (
                self._monthly_interest_manwon(
                    estimated_loan,
                    rate,
                )
            ),
            "loan_cap_note": cap_note,
            "rate_note": rate_note,
            "calculation_basis": (
                "min(보증금 부족액, 보증금의 80%, 상품 한도)"
            ),
            "disclaimer": (
                "자산심사, 보증심사 및 우대금리에 따라 "
                "실제 결과가 달라질 수 있음"
            ),
        }

    def _estimate_butimok_monthly(
        self,
        context: Mapping[str, Any],
    ) -> dict[str, Any]:
        deposit = to_float(
            context.get(
                "property_deposit_manwon"
            )
        )

        monthly_rent = to_float(
            context.get(
                "property_monthly_rent_manwon"
            )
        )

        available_cash = to_float(
            context.get(
                "available_cash_manwon"
            )
        )

        missing = []

        if deposit is None:
            missing.append(
                "property_deposit_manwon"
            )

        if monthly_rent is None:
            missing.append(
                "property_monthly_rent_manwon"
            )

        if available_cash is None:
            missing.append(
                "available_cash_manwon"
            )

        if missing:
            return {
                "calculation_status": (
                    "needs_more_info"
                ),
                "missing_fields": missing,
            }

        deposit_gap = max(
            0.0,
            deposit - available_cash,
        )

        deposit_loan = max(
            0.0,
            min(
                deposit_gap,
                4500.0,
                deposit * 0.70,
            ),
        )

        # 월 최대 50만원, 24개월, 총 1,200만원 이내
        financed_monthly_rent = min(
            monthly_rent,
            50.0,
        )

        monthly_rent_loan_total = min(
            financed_monthly_rent * 24,
            1200.0,
        )

        deposit_interest = (
            self._monthly_interest_manwon(
                deposit_loan,
                1.30,
            )
        )

        # 조사자료 기준:
        # 월 20만원까지 0%, 초과분 1.0%
        interest_bearing_monthly_part = max(
            0.0,
            financed_monthly_rent - 20.0,
        )

        interest_bearing_principal = min(
            interest_bearing_monthly_part
            * 24,
            monthly_rent_loan_total,
        )

        monthly_component_interest_upper = (
            self._monthly_interest_manwon(
                interest_bearing_principal,
                1.00,
            )
        )

        total_interest_upper = round(
            deposit_interest
            + monthly_component_interest_upper,
            2,
        )

        return {
            "calculation_status": "estimated",
            "deposit_manwon": round(
                deposit,
                2,
            ),
            "monthly_rent_manwon": round(
                monthly_rent,
                2,
            ),
            "available_cash_manwon": round(
                available_cash,
                2,
            ),
            "deposit_gap_before_loan_manwon": round(
                deposit_gap,
                2,
            ),
            "estimated_deposit_loan_manwon": round(
                deposit_loan,
                2,
            ),
            "remaining_deposit_gap_manwon": round(
                max(
                    0.0,
                    deposit_gap
                    - deposit_loan,
                ),
                2,
            ),
            "estimated_monthly_rent_loan_total_manwon": round(
                monthly_rent_loan_total,
                2,
            ),
            "deposit_loan_rate_pct": 1.30,
            "monthly_rent_loan_rate_note": (
                "월 20만원까지 0%, 초과 지원분 1.0%"
            ),
            "estimated_monthly_interest_upper_manwon": (
                total_interest_upper
            ),
            "calculation_basis": (
                "보증금 대출은 min(부족액, 4,500만원, "
                "보증금의 70%), 월세금 대출은 "
                "월 최대 50만원·24개월·총 1,200만원"
            ),
            "affordability_note": (
                "월세금 대출은 월세 자체를 없애는 지원이 아니라 "
                "향후 상환해야 하는 대출이므로 월 주거비에서 "
                "월세를 차감하지 않음"
            ),
            "disclaimer": (
                "월세 대출은 월별 실행될 수 있어 실제 이자는 "
                "실행 시점과 잔액에 따라 달라짐"
            ),
        }

    def _estimate_loan(
        self,
        product: Mapping[str, Any],
        context: Mapping[str, Any],
        has_failed_rule: bool,
    ) -> dict[str, Any]:
        if has_failed_rule:
            return {
                "calculation_status": (
                    "not_calculated_ineligible"
                )
            }

        formula_key = str(
            product.get(
                "loan_formula_key"
            )
        )

        if formula_key == "kb_youth_custom":
            return (
                self._estimate_kb_youth_custom(
                    context=context,
                    product=product,
                )
            )

        if formula_key == "youth_butimok_jeonse":
            return (
                self._estimate_butimok_jeonse(
                    context=context,
                )
            )

        if formula_key == "youth_butimok_monthly":
            return (
                self._estimate_butimok_monthly(
                    context=context,
                )
            )

        return {
            "calculation_status": (
                "unsupported_formula"
            ),
            "loan_formula_key": formula_key,
        }

    def match_product(
        self,
        product_id: str,
        user: Mapping[str, Any],
        property_info: Mapping[str, Any],
    ) -> dict[str, Any]:
        product_rows = self.products[
            self.products[
                "product_id"
            ].eq(product_id)
        ]

        if product_rows.empty:
            raise KeyError(
                f"존재하지 않는 상품: {product_id}"
            )

        product = product_rows.iloc[0].to_dict()

        context = self._build_context(
            user=user,
            property_info=property_info,
        )

        product_rules = self.rules[
            self.rules[
                "product_id"
            ].eq(product_id)
        ]

        rule_results = (
            self._check_product_compatibility(
                product=product,
                context=context,
            )
        )

        for rule in product_rules.to_dict(
            orient="records"
        ):
            rule_results.append(
                self._evaluate_rule(
                    rule=rule,
                    context=context,
                )
            )

        failed_rules = [
            result
            for result in rule_results
            if result["status"] == "failed"
        ]

        passed_rules = [
            result
            for result in rule_results
            if result["status"] == "passed"
        ]

        unresolved_rules = [
            result
            for result in rule_results
            if result["status"]
            == "needs_more_info"
        ]

        skipped_rules = [
            result
            for result in rule_results
            if result["status"] == "skipped"
        ]

        missing_fields = sorted(
            {
                field
                for result in unresolved_rules
                for field in result.get(
                    "missing_fields",
                    [],
                )
            }
        )

        if failed_rules:
            match_status = "ineligible"

        elif unresolved_rules:
            match_status = "needs_more_info"

        else:
            match_status = "likely_eligible"

        estimate = self._estimate_loan(
            product=product,
            context=context,
            has_failed_rule=bool(
                failed_rules
            ),
        )

        return {
            "product_id": product_id,
            "product_name": product[
                "product_name"
            ],
            "provider": product.get(
                "provider"
            ),
            "sales_channel": product.get(
                "sales_channel"
            ),
            "match_status": match_status,
            "availability_status": product.get(
                "availability_status"
            ),
            "passed_rule_count": len(
                passed_rules
            ),
            "failed_rule_count": len(
                failed_rules
            ),
            "unresolved_rule_count": len(
                unresolved_rules
            ),
            "missing_fields": missing_fields,
            "passed_rules": passed_rules,
            "failed_rules": failed_rules,
            "unresolved_rules": (
                unresolved_rules
            ),
            "skipped_rules": skipped_rules,
            "loan_estimate": estimate,
            "official_url": product.get(
                "official_url"
            ),
            "notes": product.get("notes"),
            "result_disclaimer": (
                "본 결과는 입력 정보와 조사된 일반 조건을 이용한 "
                "사전 매칭이며 실제 대출 승인 결과가 아닙니다."
            ),
        }

    def match_all(
        self,
        user: Mapping[str, Any],
        property_info: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        results = []

        for product_id in self.products[
            "product_id"
        ].tolist():
            results.append(
                self.match_product(
                    product_id=product_id,
                    user=user,
                    property_info=property_info,
                )
            )

        def sort_key(
            result: dict[str, Any],
        ) -> tuple[int, float]:
            remaining_gap = to_float(
                result.get(
                    "loan_estimate",
                    {},
                ).get(
                    "remaining_deposit_gap_manwon"
                ),
                float("inf"),
            )

            if remaining_gap is None:
                remaining_gap = float("inf")

            return (
                STATUS_PRIORITY.get(
                    result["match_status"],
                    99,
                ),
                remaining_gap,
            )

        return sorted(
            results,
            key=sort_key,
        )
