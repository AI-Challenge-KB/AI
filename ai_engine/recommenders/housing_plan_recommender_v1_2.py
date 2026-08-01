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
        초기자금 부족 비율에 따라
        0~25점 페널티를 계산한다.
        """

        shortfall = max(
            0.0,
            float(
                upfront_shortfall_manwon
                or 0.0
            ),
        )

        required = max(
            0.0,
            float(
                total_upfront_required_manwon
                or 0.0
            ),
        )

        if shortfall <= 0.0:
            return 0.0

        if required <= 0.0:
            return (
                cls.UPFRONT_SHORTFALL_MAX_PENALTY
            )

        shortfall_ratio = min(
            1.0,
            shortfall / required,
        )

        penalty = (
            cls.UPFRONT_SHORTFALL_MAX_PENALTY
            * shortfall_ratio
        )

        return round(
            penalty,
            4,
        )

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

        total_housing_funds = (
            cash_plan[
                "total_housing_funds_manwon"
            ]
        )

        moving_initial_cost = (
            cash_plan[
                "moving_initial_cost_manwon"
            ]
        )

        minimum_cash_reserve = (
            cash_plan[
                "minimum_cash_reserve_manwon"
            ]
        )

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

            "projected_liquid_assets_after_12_months_manwon": (
                round(
                    projected_liquid_assets,
                    2,
                )
            ),

            "projected_net_assets_after_12_months_manwon": (
                round(
                    projected_net_assets,
                    2,
                )
            ),

            "calculation_note": (
                "이사비와 최소 비상예비금을 먼저 확보한 뒤 "
                "보증금에 사용할 수 있는 금액을 계산했습니다. "
                "보증금은 자산, 주거대출은 부채로 반영했습니다."
            ),
        }

    @staticmethod
    def _resolve_finance_decision_confidence(
        finance: Mapping[str, Any],
        remaining_deposit_gap: float,
    ) -> str:
        """
        금융상품 선택 결과의 신뢰도/상태를 결정한다.

        실제 적용된 금융상품과
        available 모드에서 안내만 하는 선택형 금융상품을
        구분한다.
        """

        selection_reason = str(
            finance.get(
                "selection_reason"
            )
            or ""
        )

        match_status = str(
            finance.get(
                "match_status"
            )
            or ""
        )

        # available 모드에서
        # 실제 적용하지 않고 안내만 하는 금융상품
        if (
            selection_reason
            == (
                "optional_monthly_rent_"
                "financing_available"
            )
        ):
            if (
                match_status
                == "likely_eligible"
            ):
                return (
                    "optional_prequalified_finance"
                )

            return (
                "optional_provisional_finance"
            )

        # 실제 금융상품을 적용하지 않은 경우
        if not finance.get(
            "applied"
        ):
            if (
                remaining_deposit_gap
                <= 0
            ):
                return (
                    "no_finance_needed"
                )

            return (
                "no_applicable_finance"
            )

        # 실제 적용 + 가입 가능성이 높은 경우
        if (
            match_status
            == "likely_eligible"
        ):
            return (
                "prequalified_estimate"
            )

        # 실제 적용했으나 추가 확인이 필요한 경우
        return (
            "provisional_estimate"
        )

    @classmethod
    def _resolve_final_judgement_v12(
        cls,
        candidate: Mapping[str, Any],
        upfront_cash_shortfall: float,
        remaining_deposit_gap: float,
        reserve_shortfall: float,
    ) -> tuple[str, str]:
        """
        V1.2의 모든 재무 조건을 반영한 뒤
        최종 judgement를 한 번만 결정한다.

        우선순위:
        1. 초기자금/보증금 부족
        2. 월 현금흐름 적자
        3. 기존 점수·주거비 기준 판정
        4. 비상예비금 부족 시 추천 상한
        5. 목표 저축 미달 시 추천 상한
        """

        # -----------------------------------------
        # 1. 초기자금 부족은 hard fail
        # -----------------------------------------

        if (
            upfront_cash_shortfall > 0
            or remaining_deposit_gap > 0
        ):
            return (
                "budget_exceeded",
                "초기자금 부족",
            )

        future_simulation = (
            candidate.get(
                "future_simulation",
                {},
            )
        )

        simulation_available = bool(
            future_simulation.get(
                "available",
                False,
            )
        )

        monthly_saving_capacity = to_float(
            future_simulation.get(
                "monthly_saving_capacity_manwon"
            )
        )

        # -----------------------------------------
        # 2. 매달 적자가 발생하면 hard fail
        # -----------------------------------------

        if (
            simulation_available
            and monthly_saving_capacity is not None
            and monthly_saving_capacity < 0
        ):
            return (
                "budget_exceeded",
                "월 현금흐름 적자",
            )

        total_score = (
            to_float(
                candidate.get(
                    "score",
                    {},
                ).get(
                    "total"
                ),
                0.0,
            )
            or 0.0
        )

        affordability_ratio = (
            to_float(
                candidate.get(
                    "monthly_cost",
                    {},
                ).get(
                    "affordability_ratio"
                ),
                float("inf"),
            )
        )

        if affordability_ratio is None:
            affordability_ratio = float(
                "inf"
            )

        # -----------------------------------------
        # 3. 기존 점수/affordability 기준 판정
        # -----------------------------------------

        (
            judgement_code,
            judgement_label,
        ) = cls._final_judgement(
            total_score=total_score,
            affordability_ratio=(
                affordability_ratio
            ),
            remaining_gap=(
                remaining_deposit_gap
            ),
        )

        # -----------------------------------------
        # 4. 비상예비금 부족
        #    recommended까지만 막는다.
        # -----------------------------------------

        if (
            reserve_shortfall > 0
            and judgement_code
            == "recommended"
        ):
            judgement_code = (
                "conditionally_recommended"
            )
            judgement_label = (
                "조건부 추천"
            )

        # -----------------------------------------
        # 5. 월 현금흐름은 흑자지만
        #    목표 저축을 유지하지 못하는 경우
        # -----------------------------------------

        can_maintain_target_savings = (
            future_simulation.get(
                "can_maintain_target_savings"
            )
        )

        if (
            simulation_available
            and can_maintain_target_savings
            is False
            and judgement_code
            == "recommended"
        ):
            judgement_code = (
                "conditionally_recommended"
            )
            judgement_label = (
                "조건부 추천"
            )

        return (
            judgement_code,
            judgement_label,
        )

    def _build_candidate(
        self,
        transaction_type: str,
        row: Mapping[str, Any],
        user: Mapping[str, Any],
        affordable_budget: float,
    ) -> dict[str, Any]:
        cash_plan = (
            self._get_cash_plan(
                user
            )
        )

        # 이사비와 비상예비금을 제외한 금액만
        # 보증금에 사용할 수 있도록 전달한다.
        adjusted_user = dict(user)

        adjusted_user[
            "deposit_allocable_cash_manwon"
        ] = cash_plan[
            "deposit_allocable_cash_manwon"
        ]

        candidate = (
            super()._build_candidate(
                transaction_type=(
                    transaction_type
                ),
                row=row,
                user=adjusted_user,
                affordable_budget=(
                    affordable_budget
                ),
            )
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

        candidate[
            "initial_funds"
        ].update(
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

                "own_cash_required_for_deposit_manwon": (
                    round(
                        own_cash_required_for_deposit,
                        2,
                    )
                ),

                "total_upfront_cash_required_manwon": (
                    round(
                        total_upfront_cash_required,
                        2,
                    )
                ),

                "upfront_cash_shortfall_manwon": (
                    round(
                        upfront_cash_shortfall,
                        2,
                    )
                ),

                "reserve_shortfall_manwon": (
                    round(
                        reserve_shortfall,
                        2,
                    )
                ),

                "liquid_cash_after_move_manwon": (
                    round(
                        liquid_cash_after_move,
                        2,
                    )
                ),
            }
        )

        # -----------------------------------------
        # 금융상품 상태 정리
        # -----------------------------------------

        finance = candidate[
            "finance"
        ]

        finance[
            "used_in_cost_scenario"
        ] = bool(
            finance.get(
                "applied"
            )
        )

        finance[
            "decision_confidence"
        ] = (
            self._resolve_finance_decision_confidence(
                finance=finance,
                remaining_deposit_gap=(
                    remaining_deposit_gap
                ),
            )
        )

        # -----------------------------------------
        # 미래 자산 시뮬레이션
        # -----------------------------------------

        candidate[
            "future_simulation"
        ] = (
            self._future_simulation_v12(
                user=user,
                candidate=candidate,
                cash_plan=cash_plan,
            )
        )

        # -----------------------------------------
        # 초기자금 부족
        # -----------------------------------------

        if (
            upfront_cash_shortfall > 0
            or remaining_deposit_gap > 0
        ):
            old_total = (
                to_float(
                    candidate[
                        "score"
                    ][
                        "total"
                    ],
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

            candidate[
                "score"
            ][
                "upfront_cash_shortfall_penalty"
            ] = (
                -upfront_shortfall_penalty
            )

            candidate[
                "score"
            ][
                "total"
            ] = round(
                max(
                    0.0,
                    old_total
                    - upfront_shortfall_penalty,
                ),
                2,
            )

            candidate[
                "explanations"
            ][
                "initial_funds"
            ] = (
                f"이사비와 비상예비금을 포함하면 "
                f"초기자금이 "
                f"{upfront_cash_shortfall:,.0f}만원 "
                f"부족합니다."
            )

        # -----------------------------------------
        # 비상예비금 부족
        # -----------------------------------------

        elif reserve_shortfall > 0:
            old_total = (
                to_float(
                    candidate[
                        "score"
                    ][
                        "total"
                    ],
                    0.0,
                )
                or 0.0
            )

            candidate[
                "score"
            ][
                "cash_reserve_penalty"
            ] = (
                -self.RESERVE_SHORTFALL_PENALTY
            )

            candidate[
                "score"
            ][
                "total"
            ] = round(
                max(
                    0.0,
                    old_total
                    - self.RESERVE_SHORTFALL_PENALTY,
                ),
                2,
            )

            candidate[
                "explanations"
            ][
                "initial_funds"
            ] = (
                f"보증금과 이사비는 마련할 수 있지만, "
                f"권장 비상예비금이 "
                f"{reserve_shortfall:,.0f}만원 "
                f"부족합니다."
            )

        # -----------------------------------------
        # 초기자금 충분
        # -----------------------------------------

        else:
            candidate[
                "explanations"
            ][
                "cash_plan"
            ] = (
                f"총 주거자금 "
                f"{cash_plan['total_housing_funds_manwon']:,.0f}만원 중 "
                f"이사비 "
                f"{cash_plan['moving_initial_cost_manwon']:,.0f}만원과 "
                f"비상예비금 "
                f"{cash_plan['minimum_cash_reserve_manwon']:,.0f}만원을 "
                f"남긴 뒤 보증금 자금을 계산했습니다."
            )

        # -----------------------------------------
        # 모든 페널티 반영 후 최종 판정 1회 수행
        # -----------------------------------------

        (
            final_judgement_code,
            final_judgement_label,
        ) = (
            self._resolve_final_judgement_v12(
                candidate=candidate,
                upfront_cash_shortfall=(
                    upfront_cash_shortfall
                ),
                remaining_deposit_gap=(
                    remaining_deposit_gap
                ),
                reserve_shortfall=(
                    reserve_shortfall
                ),
            )
        )

        candidate[
            "judgement"
        ] = {
            "code": (
                final_judgement_code
            ),
            "label": (
                final_judgement_label
            ),
        }

        # -----------------------------------------
        # 미래 시뮬레이션 설명
        # -----------------------------------------

        future_simulation = (
            candidate[
                "future_simulation"
            ]
        )

        if future_simulation.get(
            "available",
            False,
        ):
            monthly_saving_capacity = (
                to_float(
                    future_simulation.get(
                        "monthly_saving_capacity_manwon"
                    ),
                    0.0,
                )
                or 0.0
            )

            target_savings = (
                to_float(
                    future_simulation.get(
                        "target_monthly_savings_manwon"
                    ),
                    0.0,
                )
                or 0.0
            )

            if monthly_saving_capacity < 0:
                future_text = (
                    f"이사 후 예상 월 현금흐름이 "
                    f"{monthly_saving_capacity:.1f}만원으로 "
                    f"적자가 예상되어 추천하지 않습니다."
                )

            elif (
                future_simulation.get(
                    "can_maintain_target_savings"
                )
                is False
            ):
                future_text = (
                    f"이사 후 월 저축 가능액은 "
                    f"{monthly_saving_capacity:.1f}만원으로 "
                    f"흑자이지만, 목표 저축액 "
                    f"{target_savings:.1f}만원을 "
                    f"유지하기 어렵습니다."
                )

            else:
                future_text = (
                    f"이사 후 월 저축 가능액은 "
                    f"{monthly_saving_capacity:.1f}만원으로, "
                    f"목표 저축액 "
                    f"{target_savings:.1f}만원을 "
                    f"유지할 수 있습니다."
                )

            candidate[
                "explanations"
            ][
                "future_simulation"
            ] = future_text

        candidate[
            "explanations"
        ][
            "final_judgement"
        ] = (
            candidate[
                "judgement"
            ][
                "label"
            ]
        )

        return candidate

    def recommend(
        self,
        user: Mapping[str, Any],
        top_n: int = 5,
    ) -> dict[str, Any]:
        cash_plan = (
            self._get_cash_plan(
                user
            )
        )

        adjusted_user = dict(
            user
        )

        adjusted_user[
            "deposit_allocable_cash_manwon"
        ] = cash_plan[
            "deposit_allocable_cash_manwon"
        ]

        result = (
            super().recommend(
                user=adjusted_user,
                top_n=top_n,
            )
        )

        result[
            "engine_version"
        ] = (
            self.ENGINE_VERSION
        )

        result[
            "cash_planning_policy"
        ] = {
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