from __future__ import annotations

from typing import Any, Mapping

from ai_engine.recommenders.housing_plan_recommender_v1 import (
    to_float,
)
from ai_engine.recommenders.housing_plan_recommender_v1_1 import (
    HousingPlanRecommenderV11,
)


class HousingPlanRecommenderV12(
    HousingPlanRecommenderV11
):
    """
    HousingPlanRecommenderV1.1 개선 버전.

    개선사항
    1. 이사 초기비용을 먼저 확보한 뒤 보증금 가용자금 계산
    2. 최소 비상예비금을 보존한 상태에서 대출 필요액 계산
    3. 초기 현금 부족액을 숨기지 않고 명시적으로 반환
    4. 금융상품이 비용 계산에 사용되었는지 별도 표시
    5. 이사 후 유동자금과 비상예비금 유지 여부 계산
    """

    ENGINE_VERSION = (
        "housing_plan_recommender_v1_2"
    )


    UPFRONT_SHORTFALL_MAX_PENALTY = 25.0
    RESERVE_SHORTFALL_PENALTY = 10.0

    @classmethod
    def _calculate_upfront_shortfall_penalty(
        cls,
        upfront_shortfall_manwon: float,
        total_upfront_required_manwon: float,
    ) -> float:
        """
        초기자금 부족 비율에 따라 0~25점 페널티를 계산한다.

        예:
        - 부족 없음: 0점
        - 필요 자금의 10% 부족: 2.5점
        - 필요 자금의 50% 부족: 12.5점
        - 필요 자금의 100% 이상 부족: 25점
        """
        shortfall = max(
            0.0,
            float(upfront_shortfall_manwon or 0.0),
        )

        required = max(
            0.0,
            float(total_upfront_required_manwon or 0.0),
        )

        if shortfall <= 0.0:
            return 0.0

        if required <= 0.0:
            return cls.UPFRONT_SHORTFALL_MAX_PENALTY

        shortfall_ratio = min(
            1.0,
            shortfall / required,
        )

        penalty = (
            cls.UPFRONT_SHORTFALL_MAX_PENALTY
            * shortfall_ratio
        )

        return round(penalty, 4)

    @staticmethod
    def _get_cash_plan(
        user: Mapping[str, Any],
    ) -> dict[str, float]:
        total_housing_funds = (
            to_float(
                user.get(
                    "housing_funds_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        moving_initial_cost = (
            to_float(
                user.get(
                    "moving_initial_cost_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        minimum_cash_reserve = (
            to_float(
                user.get(
                    "minimum_cash_reserve_manwon"
                ),
                0.0,
            )
            or 0.0
        )

        deposit_allocable_cash = max(
            0.0,
            total_housing_funds
            - moving_initial_cost
            - minimum_cash_reserve,
        )

        return {
            "total_housing_funds_manwon": round(
                total_housing_funds,
                2,
            ),
            "moving_initial_cost_manwon": round(
                moving_initial_cost,
                2,
            ),
            "minimum_cash_reserve_manwon": round(
                minimum_cash_reserve,
                2,
            ),
            "deposit_allocable_cash_manwon": round(
                deposit_allocable_cash,
                2,
            ),
        }

    @staticmethod
    def _future_simulation_v12(
        user: Mapping[str, Any],
        candidate: Mapping[str, Any],
        cash_plan: Mapping[str, float],
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
                    "1년 후 자산을 계산하지 않았습니다."
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

        deposit = (
            to_float(
                candidate[
                    "market_price"
                ][
                    "deposit_median_manwon"
                ],
                0.0,
            )
            or 0.0
        )

        estimated_loan = (
            to_float(
                candidate[
                    "initial_funds"
                ][
                    "estimated_loan_manwon"
                ],
                0.0,
            )
            or 0.0
        )

        monthly_housing_cost = (
            to_float(
                candidate[
                    "monthly_cost"
                ][
                    "total_monthly_housing_cost_manwon"
                ],
                0.0,
            )
            or 0.0
        )

        total_housing_funds = cash_plan[
            "total_housing_funds_manwon"
        ]

        moving_initial_cost = cash_plan[
            "moving_initial_cost_manwon"
        ]

        minimum_cash_reserve = cash_plan[
            "minimum_cash_reserve_manwon"
        ]

        own_cash_required_for_deposit = max(
            0.0,
            deposit - estimated_loan,
        )

        liquid_cash_after_move_raw = (
            total_housing_funds
            - own_cash_required_for_deposit
            - moving_initial_cost
        )

        upfront_cash_shortfall = max(
            0.0,
            -liquid_cash_after_move_raw,
        )

        liquid_cash_after_move = max(
            0.0,
            liquid_cash_after_move_raw,
        )

        reserve_shortfall = max(
            0.0,
            minimum_cash_reserve
            - liquid_cash_after_move,
        )

        monthly_saving_capacity = (
            monthly_income
            - living_expense
            - debt_payment
            - monthly_housing_cost
        )

        net_assets_after_move = (
            liquid_cash_after_move_raw
            + deposit
            - estimated_loan
        )

        projected_liquid_assets = (
            liquid_cash_after_move_raw
            + monthly_saving_capacity * 12
        )

        projected_net_assets = (
            net_assets_after_move
            + monthly_saving_capacity * 12
        )

        return {
            "available": True,
            "scenario_feasible_at_move_in": (
                upfront_cash_shortfall <= 0
            ),
            "monthly_income_manwon": round(
                monthly_income,
                2,
            ),
            "monthly_living_expense_manwon": round(
                living_expense,
                2,
            ),
            "monthly_debt_payment_manwon": round(
                debt_payment,
                2,
            ),
            "monthly_housing_cost_manwon": round(
                monthly_housing_cost,
                2,
            ),
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
            "own_cash_used_for_deposit_manwon": round(
                own_cash_required_for_deposit,
                2,
            ),
            "moving_initial_cost_manwon": round(
                moving_initial_cost,
                2,
            ),
            "minimum_cash_reserve_manwon": round(
                minimum_cash_reserve,
                2,
            ),
            "liquid_cash_after_move_manwon": round(
                liquid_cash_after_move,
                2,
            ),
            "upfront_cash_shortfall_manwon": round(
                upfront_cash_shortfall,
                2,
            ),
            "reserve_shortfall_manwon": round(
                reserve_shortfall,
                2,
            ),
            "maintains_minimum_cash_reserve": (
                reserve_shortfall <= 0
            ),
            "housing_deposit_asset_manwon": round(
                deposit,
                2,
            ),
            "housing_loan_liability_manwon": round(
                estimated_loan,
                2,
            ),
            "projected_liquid_assets_after_12_months_manwon": round(
                projected_liquid_assets,
                2,
            ),
            "projected_net_assets_after_12_months_manwon": round(
                projected_net_assets,
                2,
            ),
            "calculation_note": (
                "이사비와 최소 비상예비금을 먼저 확보한 뒤 "
                "보증금에 사용할 수 있는 금액을 계산했습니다. "
                "보증금은 자산, 주거대출은 부채로 반영했습니다."
            ),
        }

    def _build_candidate(
        self,
        transaction_type: str,
        row: Mapping[str, Any],
        user: Mapping[str, Any],
        affordable_budget: float,
    ) -> dict[str, Any]:
        cash_plan = self._get_cash_plan(user)

        # 금융상품 대출액을 계산할 때는
        # 이사비와 비상예비금을 제외한 자금만 보증금 자금으로 전달한다.
        adjusted_user = dict(user)

        adjusted_user[
            "housing_funds_manwon"
        ] = cash_plan[
            "deposit_allocable_cash_manwon"
        ]

        candidate = super()._build_candidate(
            transaction_type=transaction_type,
            row=row,
            user=adjusted_user,
            affordable_budget=affordable_budget,
        )

        deposit = (
            to_float(
                candidate[
                    "market_price"
                ][
                    "deposit_median_manwon"
                ],
                0.0,
            )
            or 0.0
        )

        estimated_loan = (
            to_float(
                candidate[
                    "initial_funds"
                ][
                    "estimated_loan_manwon"
                ],
                0.0,
            )
            or 0.0
        )

        remaining_deposit_gap = (
            to_float(
                candidate[
                    "initial_funds"
                ][
                    "remaining_gap_after_loan_manwon"
                ],
                0.0,
            )
            or 0.0
        )

        own_cash_required_for_deposit = max(
            0.0,
            deposit - estimated_loan,
        )

        total_upfront_cash_required = (
            own_cash_required_for_deposit
            + cash_plan[
                "moving_initial_cost_manwon"
            ]
            + cash_plan[
                "minimum_cash_reserve_manwon"
            ]
        )

        upfront_cash_shortfall = max(
            0.0,
            total_upfront_cash_required
            - cash_plan[
                "total_housing_funds_manwon"
            ],
        )

        liquid_cash_after_move = max(
            0.0,
            cash_plan[
                "total_housing_funds_manwon"
            ]
            - own_cash_required_for_deposit
            - cash_plan[
                "moving_initial_cost_manwon"
            ],
        )

        reserve_shortfall = max(
            0.0,
            cash_plan[
                "minimum_cash_reserve_manwon"
            ]
            - liquid_cash_after_move,
        )

        candidate["initial_funds"].update(
            {
                "total_housing_funds_manwon": (
                    cash_plan[
                        "total_housing_funds_manwon"
                    ]
                ),
                "deposit_allocable_cash_manwon": (
                    cash_plan[
                        "deposit_allocable_cash_manwon"
                    ]
                ),
                "moving_initial_cost_manwon": (
                    cash_plan[
                        "moving_initial_cost_manwon"
                    ]
                ),
                "minimum_cash_reserve_manwon": (
                    cash_plan[
                        "minimum_cash_reserve_manwon"
                    ]
                ),
                "own_cash_required_for_deposit_manwon": round(
                    own_cash_required_for_deposit,
                    2,
                ),
                "total_upfront_cash_required_manwon": round(
                    total_upfront_cash_required,
                    2,
                ),
                "upfront_cash_shortfall_manwon": round(
                    upfront_cash_shortfall,
                    2,
                ),
                "reserve_shortfall_manwon": round(
                    reserve_shortfall,
                    2,
                ),
                "liquid_cash_after_move_manwon": round(
                    liquid_cash_after_move,
                    2,
                ),
            }
        )

        finance = candidate["finance"]

        finance["used_in_cost_scenario"] = bool(
            finance.get("applied")
        )

        if not finance.get("applied"):
            decision_confidence = (
                "no_finance_needed"
                if remaining_deposit_gap <= 0
                else "no_applicable_finance"
            )

        elif (
            finance.get("match_status")
            == "likely_eligible"
        ):
            decision_confidence = (
                "prequalified_estimate"
            )

        else:
            decision_confidence = (
                "provisional_estimate"
            )

        finance[
            "decision_confidence"
        ] = decision_confidence

        candidate["future_simulation"] = (
            self._future_simulation_v12(
                user=user,
                candidate=candidate,
                cash_plan=cash_plan,
            )
        )

        if (
            upfront_cash_shortfall > 0
            or remaining_deposit_gap > 0
        ):
            old_total = (
                to_float(
                    candidate[
                        "score"
                    ]["total"],
                    0.0,
                )
                or 0.0
            )

            upfront_shortfall_penalty = (
                self._calculate_upfront_shortfall_penalty(
                    upfront_shortfall_manwon=(
                        upfront_cash_shortfall
                    ),
                    total_upfront_required_manwon=(
                        total_upfront_cash_required
                    ),
                )
            )

            candidate["score"][
                "upfront_cash_shortfall_penalty"
            ] = -upfront_shortfall_penalty

            candidate["score"]["total"] = round(
                max(
                    0.0,
                    old_total
                    - upfront_shortfall_penalty,
                ),
                2,
            )

            candidate["judgement"] = {
                "code": "budget_exceeded",
                "label": "초기자금 부족",
            }

            candidate[
                "explanations"
            ]["initial_funds"] = (
                f"이사비와 비상예비금을 포함하면 "
                f"초기자금이 "
                f"{upfront_cash_shortfall:,.0f}만원 부족합니다."
            )

        elif reserve_shortfall > 0:
            old_total = (
                to_float(
                    candidate[
                        "score"
                    ]["total"],
                    0.0,
                )
                or 0.0
            )

            candidate["score"][
                "cash_reserve_penalty"
            ] = -self.RESERVE_SHORTFALL_PENALTY

            candidate["score"]["total"] = round(
                max(
                    0.0,
                    old_total
                    - self.RESERVE_SHORTFALL_PENALTY,
                ),
                2,
            )

            if (
                candidate[
                    "judgement"
                ]["code"]
                == "recommended"
            ):
                candidate["judgement"] = {
                    "code": (
                        "conditionally_recommended"
                    ),
                    "label": "조건부 추천",
                }

            candidate[
                "explanations"
            ]["initial_funds"] = (
                f"보증금과 이사비는 마련할 수 있지만, "
                f"권장 비상예비금이 "
                f"{reserve_shortfall:,.0f}만원 부족합니다."
            )

        else:
            candidate[
                "explanations"
            ]["cash_plan"] = (
                f"총 주거자금 "
                f"{cash_plan['total_housing_funds_manwon']:,.0f}만원 중 "
                f"이사비 "
                f"{cash_plan['moving_initial_cost_manwon']:,.0f}만원과 "
                f"비상예비금 "
                f"{cash_plan['minimum_cash_reserve_manwon']:,.0f}만원을 "
                f"남긴 뒤 보증금 자금을 계산했습니다."
            )

        candidate[
            "explanations"
        ]["final_judgement"] = (
            candidate[
                "judgement"
            ]["label"]
        )

        return candidate

    def recommend(
        self,
        user: Mapping[str, Any],
        top_n: int = 5,
    ) -> dict[str, Any]:
        result = super().recommend(
            user=user,
            top_n=top_n,
        )

        result["engine_version"] = (
            self.ENGINE_VERSION
        )

        result["cash_planning_policy"] = {
            "calculation_order": [
                "total_housing_funds",
                "moving_initial_cost",
                "minimum_cash_reserve",
                "deposit_allocable_cash",
                "estimated_loan",
            ],
            "upfront_shortfall_policy": (
                "초기자금 부족 판정"
            ),
            "reserve_shortfall_policy": (
                "조건부 추천 이하로 제한"
            ),
        }

        return result
