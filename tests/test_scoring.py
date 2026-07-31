import pytest

from ai_engine.recommendation.scoring import (
    calculate_affordability_score,
    evaluate_affordability,
)


def test_plan_within_budget() -> None:
    result = evaluate_affordability(
        affordable_budget=700_000,
        net_monthly_cost=650_000,
    )

    assert result["is_within_budget"] is True
    assert result["remaining_budget"] == 50_000
    assert result["over_budget_amount"] == 0
    assert result["affordability_score"] == 100.0
    assert result["affordability_status"] == "within_budget"


def test_plan_slightly_over_budget() -> None:
    result = evaluate_affordability(
        affordable_budget=700_000,
        net_monthly_cost=735_000,
    )

    assert result["is_within_budget"] is False
    assert result["remaining_budget"] == 0
    assert result["over_budget_amount"] == 35_000
    assert result["affordability_status"] == (
        "slightly_over_budget"
    )


def test_plan_far_over_budget() -> None:
    score = calculate_affordability_score(
        affordable_budget=700_000,
        net_monthly_cost=1_050_000,
    )

    assert score == 0.0


def test_negative_cost_raises_error() -> None:
    with pytest.raises(ValueError):
        evaluate_affordability(
            affordable_budget=700_000,
            net_monthly_cost=-1,
        )
