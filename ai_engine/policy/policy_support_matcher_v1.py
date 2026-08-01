from __future__ import annotations

from datetime import date
from typing import Any, Mapping


YOUTH_MONTHLY_RENT_SUPPORT_ID = (
    "youth_monthly_rent_support"
)

YOUTH_HOUSING_DREAM_SAVINGS_ID = (
    "youth_housing_dream_savings"
)


def _parse_date(
    value: Any,
) -> date | None:
    if value is None:
        return None

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        try:
            return date.fromisoformat(
                value
            )
        except ValueError:
            return None

    return None


def _calculate_age(
    birth_date: Any,
    evaluation_date: Any,
) -> int | None:
    birth = _parse_date(
        birth_date
    )

    evaluation = _parse_date(
        evaluation_date
    )

    if birth is None:
        return None

    if evaluation is None:
        evaluation = date.today()

    age = (
        evaluation.year
        - birth.year
    )

    if (
        evaluation.month,
        evaluation.day,
    ) < (
        birth.month,
        birth.day,
    ):
        age -= 1

    return age


def _to_float(
    value: Any,
    default: float = 0.0,
) -> float:
    if value is None:
        return default

    try:
        return float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return default


class PolicySupportMatcherV1:
    """
    주거 관련 정책지원과 장기 저축상품을
    금융대출과 별도의 레이어에서 판정한다.

    현재 지원 대상:
    D. 청년월세지원
    E. 청년 주택드림 청약통장

    원칙:
    - 지원금을 대출로 취급하지 않는다.
    - 정책지원이 아직 확정되지 않은 상태에서는
      현재 추천 비용에서 자동 차감하지 않는다.
    - 장기 저축상품은 현재 주거비 또는
      보증금 부족액을 줄이지 않는다.
    """

    D_APPLICATION_START = date(
        2026,
        3,
        30,
    )

    D_APPLICATION_END = date(
        2026,
        5,
        29,
    )

    D_MAX_MONTHLY_SUPPORT_MANWON = (
        20.0
    )

    def match_all(
        self,
        user: Mapping[str, Any],
        property_info: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        return [
            self._match_monthly_rent_support(
                user=user,
                property_info=property_info,
            ),
            self._match_housing_dream_savings(
                user=user,
            ),
        ]

    def _match_monthly_rent_support(
        self,
        user: Mapping[str, Any],
        property_info: Mapping[str, Any],
    ) -> dict[str, Any]:
        """
        D. 청년월세지원 판정.

        현재 서비스에 없는 소득·자산 세부 요건은
        임의 추정하지 않고 needs_more_info로 처리한다.

        정책 승인 전에는 실제 월 주거비에서
        지원액을 자동 차감하지 않는다.
        """

        evaluation_date = (
            _parse_date(
                user.get(
                    "evaluation_date"
                )
            )
            or date.today()
        )

        age = _calculate_age(
            birth_date=user.get(
                "birth_date"
            ),
            evaluation_date=(
                evaluation_date
            ),
        )

        contract_type = str(
            property_info.get(
                "contract_type"
            )
            or ""
        )

        monthly_rent = max(
            0.0,
            _to_float(
                property_info.get(
                    "monthly_rent_manwon"
                )
            ),
        )

        base_result = {
            "support_id": (
                YOUTH_MONTHLY_RENT_SUPPORT_ID
            ),
            "support_code": "D",
            "support_name": (
                "청년월세지원"
            ),
            "support_type": (
                "monthly_grant"
            ),

            # 보증금 대출이 아님
            "affects_deposit_gap": False,

            # 승인 전에는 비용에 자동 적용하지 않음
            "used_in_cost_scenario": False,

            "potential_monthly_support_manwon": (
                min(
                    monthly_rent,
                    self.D_MAX_MONTHLY_SUPPORT_MANWON,
                )
            ),

            "applied_monthly_support_manwon": (
                0.0
            ),

            "missing_fields": [],
            "reason_codes": [],
        }

        # ----------------------------------------
        # 계약형태
        # ----------------------------------------

        if (
            contract_type
            != "monthly_rent"
        ):
            return {
                **base_result,
                "match_status": (
                    "ineligible"
                ),
                "application_status": (
                    "not_applicable"
                ),
                "currently_applicable": (
                    False
                ),
                "reason_codes": [
                    "monthly_rent_contract_required",
                ],
            }

        # ----------------------------------------
        # 연령
        # ----------------------------------------

        if age is None:
            return {
                **base_result,
                "match_status": (
                    "needs_more_info"
                ),
                "application_status": (
                    self._resolve_d_application_status(
                        evaluation_date
                    )
                ),
                "currently_applicable": (
                    False
                ),
                "missing_fields": [
                    "birth_date",
                ],
                "reason_codes": [
                    "age_not_confirmed",
                ],
            }

        if (
            age < 19
            or age > 34
        ):
            return {
                **base_result,
                "match_status": (
                    "ineligible"
                ),
                "application_status": (
                    "not_applicable"
                ),
                "currently_applicable": (
                    False
                ),
                "reason_codes": [
                    "age_requirement_not_met",
                ],
            }

        # ----------------------------------------
        # 소득·자산 세부 요건
        #
        # 현재 UserProfileRequest에는
        # 아래 판정을 정확히 할 정보가 부족하다.
        # 숫자를 임의 환산하지 않는다.
        # ----------------------------------------

        eligibility_fields = {
            "youth_household_income_eligible": (
                user.get(
                    "youth_household_income_eligible"
                )
            ),
            "origin_household_income_eligible": (
                user.get(
                    "origin_household_income_eligible"
                )
            ),
            "youth_household_assets_eligible": (
                user.get(
                    "youth_household_assets_eligible"
                )
            ),
            "origin_household_assets_eligible": (
                user.get(
                    "origin_household_assets_eligible"
                )
            ),
        }

        # 하나라도 명확히 False면 부적격
        failed_fields = [
            field
            for field, value
            in eligibility_fields.items()
            if value is False
        ]

        if failed_fields:
            return {
                **base_result,
                "match_status": (
                    "ineligible"
                ),
                "application_status": (
                    self._resolve_d_application_status(
                        evaluation_date
                    )
                ),
                "currently_applicable": (
                    False
                ),
                "reason_codes": [
                    "income_or_asset_requirement_not_met",
                ],
            }

        missing_fields = [
            field
            for field, value
            in eligibility_fields.items()
            if value is None
        ]

        application_status = (
            self._resolve_d_application_status(
                evaluation_date
            )
        )

        if missing_fields:
            return {
                **base_result,
                "match_status": (
                    "needs_more_info"
                ),
                "application_status": (
                    application_status
                ),
                "currently_applicable": (
                    False
                ),
                "missing_fields": (
                    missing_fields
                ),
                "reason_codes": [
                    "income_and_asset_review_required",
                ],
            }

        # 소득·자산 요건을 모두 충족해도
        # 접수기간이 종료됐다면 현재 적용은 불가능
        if (
            application_status
            != "open"
        ):
            return {
                **base_result,
                "match_status": (
                    "likely_eligible"
                ),
                "application_status": (
                    application_status
                ),
                "currently_applicable": (
                    False
                ),
                "reason_codes": [
                    "eligible_but_application_not_open",
                ],
            }

        return {
            **base_result,
            "match_status": (
                "likely_eligible"
            ),
            "application_status": (
                "open"
            ),

            # 신청 가능하다는 뜻이지
            # 실제 지원 확정이라는 뜻은 아님
            "currently_applicable": True,

            "reason_codes": [
                "basic_requirements_met",
            ],
        }

    def _match_housing_dream_savings(
        self,
        user: Mapping[str, Any],
    ) -> dict[str, Any]:
        """
        E. 청년 주택드림 청약통장.

        임차자금 대출이나 월세지원이 아니므로
        현재 후보의 보증금 부족액 또는
        월 주거비 계산에는 사용하지 않는다.
        """

        evaluation_date = (
            _parse_date(
                user.get(
                    "evaluation_date"
                )
            )
            or date.today()
        )

        age = _calculate_age(
            birth_date=user.get(
                "birth_date"
            ),
            evaluation_date=(
                evaluation_date
            ),
        )

        is_no_home = user.get(
            "is_no_home"
        )

        # 반드시 개인 연소득을 사용한다.
        # 월 실수령액 * 12로 추정하지 않는다.
        individual_annual_income = (
            user.get(
                "individual_annual_income_manwon"
            )
        )

        base_result = {
            "support_id": (
                YOUTH_HOUSING_DREAM_SAVINGS_ID
            ),
            "support_code": "E",
            "support_name": (
                "청년 주택드림 청약통장"
            ),
            "support_type": (
                "long_term_savings"
            ),
            "affects_deposit_gap": False,
            "used_in_cost_scenario": False,
            "potential_monthly_support_manwon": (
                0.0
            ),
            "applied_monthly_support_manwon": (
                0.0
            ),
            "application_status": (
                "informational"
            ),
            "currently_applicable": False,
            "missing_fields": [],
            "reason_codes": [],
        }

        if age is None:
            return {
                **base_result,
                "match_status": (
                    "needs_more_info"
                ),
                "missing_fields": [
                    "birth_date",
                ],
                "reason_codes": [
                    "age_not_confirmed",
                ],
            }

        if (
            age < 19
            or age > 34
        ):
            return {
                **base_result,
                "match_status": (
                    "ineligible"
                ),
                "reason_codes": [
                    "age_requirement_not_met",
                ],
            }

        if is_no_home is False:
            return {
                **base_result,
                "match_status": (
                    "ineligible"
                ),
                "reason_codes": [
                    "no_home_requirement_not_met",
                ],
            }

        missing_fields: list[str] = []

        if is_no_home is None:
            missing_fields.append(
                "is_no_home"
            )

        if (
            individual_annual_income
            is None
        ):
            missing_fields.append(
                "individual_annual_income_manwon"
            )

        if missing_fields:
            return {
                **base_result,
                "match_status": (
                    "needs_more_info"
                ),
                "missing_fields": (
                    missing_fields
                ),
                "reason_codes": [
                    "eligibility_information_missing",
                ],
            }

        annual_income = _to_float(
            individual_annual_income
        )

        if annual_income > 5000:
            return {
                **base_result,
                "match_status": (
                    "ineligible"
                ),
                "reason_codes": [
                    "annual_income_limit_exceeded",
                ],
            }

        return {
            **base_result,
            "match_status": (
                "likely_eligible"
            ),
            "reason_codes": [
                "basic_requirements_met",
            ],
        }

    def _resolve_d_application_status(
        self,
        evaluation_date: date,
    ) -> str:
        if (
            evaluation_date
            < self.D_APPLICATION_START
        ):
            return "not_yet_open"

        if (
            evaluation_date
            > self.D_APPLICATION_END
        ):
            return "closed"

        return "open"