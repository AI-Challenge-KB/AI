from ai_engine.recommenders.housing_plan_recommender_v1_2 import (
    HousingPlanRecommenderV12,
)


def make_candidate(
    *,
    score=85,
    affordability_ratio=0.9,
    monthly_saving_capacity=50,
    target_savings=30,
    can_maintain_target_savings=True,
):
    return {
        "score": {
            "total": score,
        },
        "monthly_cost": {
            "affordability_ratio": (
                affordability_ratio
            ),
        },
        "future_simulation": {
            "available": True,
            "monthly_saving_capacity_manwon": (
                monthly_saving_capacity
            ),
            "target_monthly_savings_manwon": (
                target_savings
            ),
            "can_maintain_target_savings": (
                can_maintain_target_savings
            ),
        },
    }


def test_negative_monthly_cashflow_is_budget_exceeded():
    candidate = make_candidate(
        score=95,
        affordability_ratio=0.8,
        monthly_saving_capacity=-10,
        can_maintain_target_savings=False,
    )

    code, label = (
        HousingPlanRecommenderV12
        ._resolve_final_judgement_v12(
            candidate=candidate,
            upfront_cash_shortfall=0,
            remaining_deposit_gap=0,
            reserve_shortfall=0,
        )
    )

    assert code == "budget_exceeded"
    assert label == "월 현금흐름 적자"


def test_initial_cash_shortfall_is_budget_exceeded():
    candidate = make_candidate(
        score=95,
        monthly_saving_capacity=100,
    )

    code, label = (
        HousingPlanRecommenderV12
        ._resolve_final_judgement_v12(
            candidate=candidate,
            upfront_cash_shortfall=500,
            remaining_deposit_gap=0,
            reserve_shortfall=0,
        )
    )

    assert code == "budget_exceeded"
    assert label == "초기자금 부족"


def test_remaining_deposit_gap_is_budget_exceeded():
    candidate = make_candidate(
        score=95,
        monthly_saving_capacity=100,
    )

    code, _ = (
        HousingPlanRecommenderV12
        ._resolve_final_judgement_v12(
            candidate=candidate,
            upfront_cash_shortfall=0,
            remaining_deposit_gap=300,
            reserve_shortfall=0,
        )
    )

    assert code == "budget_exceeded"


def test_target_savings_failure_caps_recommendation():
    candidate = make_candidate(
        score=90,
        affordability_ratio=0.8,
        monthly_saving_capacity=20,
        target_savings=50,
        can_maintain_target_savings=False,
    )

    code, label = (
        HousingPlanRecommenderV12
        ._resolve_final_judgement_v12(
            candidate=candidate,
            upfront_cash_shortfall=0,
            remaining_deposit_gap=0,
            reserve_shortfall=0,
        )
    )

    assert (
        code
        == "conditionally_recommended"
    )

    assert label == "조건부 추천"


def test_reserve_shortfall_caps_recommendation():
    candidate = make_candidate(
        score=90,
        affordability_ratio=0.8,
        monthly_saving_capacity=80,
        can_maintain_target_savings=True,
    )

    code, label = (
        HousingPlanRecommenderV12
        ._resolve_final_judgement_v12(
            candidate=candidate,
            upfront_cash_shortfall=0,
            remaining_deposit_gap=0,
            reserve_shortfall=100,
        )
    )

    assert (
        code
        == "conditionally_recommended"
    )

    assert label == "조건부 추천"


def test_good_financial_scenario_can_remain_recommended():
    candidate = make_candidate(
        score=90,
        affordability_ratio=0.9,
        monthly_saving_capacity=80,
        target_savings=50,
        can_maintain_target_savings=True,
    )

    code, label = (
        HousingPlanRecommenderV12
        ._resolve_final_judgement_v12(
            candidate=candidate,
            upfront_cash_shortfall=0,
            remaining_deposit_gap=0,
            reserve_shortfall=0,
        )
    )

    assert code == "recommended"
    assert label == "추천"


def test_existing_lower_judgement_is_not_upgraded():
    candidate = make_candidate(
        score=60,
        affordability_ratio=1.05,
        monthly_saving_capacity=50,
        can_maintain_target_savings=False,
    )

    code, _ = (
        HousingPlanRecommenderV12
        ._resolve_final_judgement_v12(
            candidate=candidate,
            upfront_cash_shortfall=0,
            remaining_deposit_gap=0,
            reserve_shortfall=0,
        )
    )

    assert code == "consider_other_area"
