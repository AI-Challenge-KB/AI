from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ai_engine.recommenders.housing_plan_recommender_v1 import (
    HousingPlanRecommenderV1,
    is_missing,
    to_float,
)


class HousingPlanRecommenderV11(
    HousingPlanRecommenderV1
):
    """
    HousingPlanRecommenderV1 개선 버전.

    개선사항
    1. 월세·전세 모두 비교 시 계약 유형별 결과 다양성 보장
    2. needs_more_info 금융상품을 확정 대출처럼 판단하지 않음
    3. 금융정보가 불완전하면 최종 판단을 최소 조건부 추천으로 제한
    4. 1년 후 자산을 순자산과 유동자금으로 분리
    5. 금융 적용 전·후 비용 시나리오를 함께 반환
    """

    ENGINE_VERSION = (
        "housing_plan_recommender_v1_1"
    )

    FINANCE_UNCERTAINTY_PENALTY = 8.0

    @staticmethod
    def _diversify_candidates(
        candidates: list[dict[str, Any]],
        top_n: int,
    ) -> list[dict[str, Any]]:
        """
        전체 순위를 최대한 유지하면서 월세·전세가 모두 존재하면
        계약 형태별 최소 1개씩 결과에 포함한다.
        """
        if top_n <= 0:
            return []

        selected: list[dict[str, Any]] = []
        selected_ids: set[str] = set()
        selected_types: set[str] = set()

        available_types = {
            candidate["transaction_type"]
            for candidate in candidates
        }

        # 계약 유형별 최고 순위 후보를 먼저 한 개씩 확보한다.
        if (
            len(available_types) >= 2
            and top_n >= 2
        ):
            for candidate in candidates:
                transaction_type = candidate[
                    "transaction_type"
                ]

                if transaction_type in selected_types:
                    continue

                selected.append(candidate)
                selected_ids.add(
                    candidate["candidate_id"]
                )
                selected_types.add(
                    transaction_type
                )

                if (
                    selected_types
                    == available_types
                    or len(selected) >= top_n
                ):
                    break

        # 동일 지역·주택 유형의 반복 노출을 줄인다.
        seen_diversity_keys = {
            (
                candidate["transaction_type"],
                candidate["district_name"],
                candidate["housing_type"],
            )
            for candidate in selected
        }

        for candidate in candidates:
            if len(selected) >= top_n:
                break

            candidate_id = candidate[
                "candidate_id"
            ]

            if candidate_id in selected_ids:
                continue

            diversity_key = (
                candidate["transaction_type"],
                candidate["district_name"],
                candidate["housing_type"],
            )

            if diversity_key in seen_diversity_keys:
                continue

            selected.append(candidate)
            selected_ids.add(candidate_id)
            seen_diversity_keys.add(
                diversity_key
            )

        # 아직 부족하면 원래 순위대로 채운다.
        for candidate in candidates:
            if len(selected) >= top_n:
                break

            candidate_id = candidate[
                "candidate_id"
            ]

            if candidate_id in selected_ids:
                continue

            selected.append(candidate)
            selected_ids.add(candidate_id)

        return selected

    @staticmethod
    def _future_simulation_v11(
        user: Mapping[str, Any],
        candidate: Mapping[str, Any],
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

        current_housing_funds = (
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

        # 보증금 중 자기자금으로 마련하는 부분
        own_cash_required_for_deposit = max(
            0.0,
            deposit - estimated_loan,
        )

        own_cash_used_for_deposit = min(
            current_housing_funds,
            own_cash_required_for_deposit,
        )

        liquid_cash_after_move = max(
            0.0,
            current_housing_funds
            - own_cash_used_for_deposit
            - moving_initial_cost,
        )

        monthly_saving_capacity = (
            monthly_income
            - living_expense
            - debt_payment
            - monthly_housing_cost
        )

        # 보증금은 사라지는 비용이 아니라 임차보증금 자산이다.
        # 대출로 마련한 부분은 동시에 부채로 반영한다.
        net_assets_after_move = (
            liquid_cash_after_move
            + deposit
            - estimated_loan
        )

        projected_liquid_assets = (
            liquid_cash_after_move
            + monthly_saving_capacity * 12
        )

        projected_net_assets = (
            net_assets_after_move
            + monthly_saving_capacity * 12
        )

        return {
            "available": True,
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
            "moving_initial_cost_manwon": round(
                moving_initial_cost,
                2,
            ),
            "own_cash_used_for_deposit_manwon": round(
                own_cash_used_for_deposit,
                2,
            ),
            "liquid_cash_after_move_manwon": round(
                liquid_cash_after_move,
                2,
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
                "보증금은 자산, 주거대출은 부채로 반영했습니다. "
                "월 소득과 비용이 12개월 동안 동일하다고 가정한 "
                "단순 시뮬레이션입니다."
            ),
        }

    def _build_candidate(
        self,
        transaction_type: str,
        row: Mapping[str, Any],
        user: Mapping[str, Any],
        affordable_budget: float,
    ) -> dict[str, Any]:
        candidate = super()._build_candidate(
            transaction_type=transaction_type,
            row=row,
            user=user,
            affordable_budget=affordable_budget,
        )

        finance = candidate["finance"]

        initial_gap = (
            to_float(
                candidate[
                    "initial_funds"
                ][
                    "deposit_gap_before_loan_manwon"
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

        monthly_interest = (
            to_float(
                candidate[
                    "monthly_cost"
                ][
                    "loan_interest_manwon"
                ],
                0.0,
            )
            or 0.0
        )

        base_monthly_cost = (
            to_float(
                candidate[
                    "monthly_cost"
                ][
                    "monthly_rent_manwon"
                ],
                0.0,
            )
            or 0.0
        )

        base_monthly_cost += (
            to_float(
                candidate[
                    "monthly_cost"
                ][
                    "management_fee_assumption_manwon"
                ],
                0.0,
            )
            or 0.0
        )

        base_monthly_cost += (
            to_float(
                candidate[
                    "monthly_cost"
                ][
                    "utilities_assumption_manwon"
                ],
                0.0,
            )
            or 0.0
        )

        match_status = finance.get(
            "match_status"
        )

        if not finance.get("applied"):
            finance_mode = "not_needed_or_unavailable"

        elif match_status == "likely_eligible":
            finance_mode = (
                "prequalified_estimate"
            )

        else:
            finance_mode = (
                "provisional_needs_confirmation"
            )

        finance["application_mode"] = (
            finance_mode
        )

        finance[
            "used_for_final_judgement"
        ] = (
            finance_mode
            == "prequalified_estimate"
        )

        candidate["cost_scenarios"] = {
            "without_finance": {
                "deposit_gap_manwon": round(
                    initial_gap,
                    2,
                ),
                "monthly_housing_cost_manwon": round(
                    base_monthly_cost,
                    2,
                ),
            },
            "with_estimated_finance": {
                "estimated_loan_manwon": round(
                    estimated_loan,
                    2,
                ),
                "estimated_monthly_interest_manwon": round(
                    monthly_interest,
                    2,
                ),
                "remaining_deposit_gap_manwon": (
                    candidate[
                        "initial_funds"
                    ][
                        "remaining_gap_after_loan_manwon"
                    ]
                ),
                "monthly_housing_cost_manwon": (
                    candidate[
                        "monthly_cost"
                    ][
                        "total_monthly_housing_cost_manwon"
                    ]
                ),
                "finance_status": (
                    match_status
                ),
            },
        }

        # 추가 정보가 필요한 금융상품을 사용했다면
        # 확정 추천으로 표시하지 않는다.
        if (
            finance.get("applied")
            and match_status == "needs_more_info"
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

            adjusted_total = max(
                0.0,
                old_total
                - self.FINANCE_UNCERTAINTY_PENALTY,
            )

            candidate["score"][
                "finance_uncertainty_penalty"
            ] = (
                -self.FINANCE_UNCERTAINTY_PENALTY
            )

            candidate["score"]["total"] = round(
                adjusted_total,
                2,
            )

            current_code = candidate[
                "judgement"
            ]["code"]

            if current_code == "recommended":
                candidate["judgement"] = {
                    "code": (
                        "conditionally_recommended"
                    ),
                    "label": "조건부 추천",
                }

            candidate[
                "explanations"
            ]["finance"] += (
                " 다만 일부 자격조건이 확인되지 않았으므로 "
                "이 대출을 확정적으로 적용할 수 없고, "
                "최종 판단은 조건부 추천으로 제한했습니다."
            )

            candidate[
                "explanations"
            ]["final_judgement"] = (
                candidate[
                    "judgement"
                ]["label"]
            )

        candidate["future_simulation"] = (
            self._future_simulation_v11(
                user=user,
                candidate=candidate,
            )
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

        transaction_type_counts = Counter(
            recommendation[
                "transaction_type"
            ]
            for recommendation in result[
                "recommendations"
            ]
        )

        result["output_balance"] = {
            "monthly_rent_count": (
                transaction_type_counts.get(
                    "monthly_rent",
                    0,
                )
            ),
            "jeonse_count": (
                transaction_type_counts.get(
                    "jeonse",
                    0,
                )
            ),
            "contract_type_diversity_applied": (
                len(transaction_type_counts)
                >= 2
            ),
        }

        result["decision_policy"] = {
            "needs_more_info_finance": (
                "조건부 추천 이하로 제한"
            ),
            "likely_eligible_finance": (
                "예상 대출액을 반영하되 실제 승인 아님"
            ),
            "contract_type_balance": (
                "월세·전세 모두 비교 시 각 유형 최소 1개 노출"
            ),
        }

        return result
