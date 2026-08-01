import pytest

from ai_engine.calculators.affordable_budget import (
    calculate_affordable_housing_budget_manwon,
)


def test_basic_affordable_budget():
    result = calculate_affordable_housing_budget_manwon(
        monthly_income_manwon=300,
        living_expense_manwon=100,
        debt_payment_manwon=20,
        target_savings_manwon=50,
    )

    assert result["total_monthly_income_manwon"] == 300
    assert result["mandatory_cost_manwon"] == 120
    assert result["preserved_savings_manwon"] == 50
    assert result["preserved_emergency_fund_manwon"] == 0
    assert result["affordable_housing_budget_manwon"] == 130


def test_additional_income_is_included():
    result = calculate_affordable_housing_budget_manwon(
        monthly_income_manwon=250,
        additional_income_manwon=50,
        living_expense_manwon=100,
        target_savings_manwon=50,
    )

    assert result["total_monthly_income_manwon"] == 300
    assert result["affordable_housing_budget_manwon"] == 150


def test_zero_income_returns_zero_budget():
    result = calculate_affordable_housing_budget_manwon(
        monthly_income_manwon=0,
        living_expense_manwon=50,
        debt_payment_manwon=10,
    )

    assert result["affordable_housing_budget_manwon"] == 0


def test_negative_residual_is_clamped_to_zero():
    result = calculate_affordable_housing_budget_manwon(
        monthly_income_manwon=100,
        living_expense_manwon=120,
        debt_payment_manwon=20,
        target_savings_manwon=30,
    )

    assert result["affordable_housing_budget_manwon"] == 0


def test_savings_preservation_ratio_is_applied():
    result = calculate_affordable_housing_budget_manwon(
        monthly_income_manwon=300,
        living_expense_manwon=100,
        target_savings_manwon=100,
        savings_preservation_ratio=0.5,
    )

    assert result["preserved_savings_manwon"] == 50
    assert result["affordable_housing_budget_manwon"] == 150


def test_emergency_fund_preservation_is_applied():
    result = calculate_affordable_housing_budget_manwon(
        monthly_income_manwon=300,
        living_expense_manwon=100,
        target_emergency_fund_contribution_manwon=40,
        emergency_fund_preservation_ratio=0.5,
    )

    assert result["preserved_emergency_fund_manwon"] == 20
    assert result["affordable_housing_budget_manwon"] == 180


def test_savings_and_emergency_fund_are_both_preserved():
    result = calculate_affordable_housing_budget_manwon(
        monthly_income_manwon=300,
        living_expense_manwon=100,
        debt_payment_manwon=20,
        target_savings_manwon=50,
        savings_preservation_ratio=1.0,
        target_emergency_fund_contribution_manwon=30,
        emergency_fund_preservation_ratio=1.0,
    )

    assert result["affordable_housing_budget_manwon"] == 100


@pytest.mark.parametrize(
    "field_name",
    [
        "monthly_income_manwon",
        "additional_income_manwon",
        "living_expense_manwon",
        "debt_payment_manwon",
        "target_savings_manwon",
        "target_emergency_fund_contribution_manwon",
    ],
)
def test_negative_money_values_are_rejected(field_name):
    kwargs = {
        "monthly_income_manwon": 300,
        "additional_income_manwon": 0,
        "living_expense_manwon": 100,
        "debt_payment_manwon": 0,
        "target_savings_manwon": 0,
        "target_emergency_fund_contribution_manwon": 0,
    }

    kwargs[field_name] = -1

    with pytest.raises(ValueError):
        calculate_affordable_housing_budget_manwon(
            **kwargs
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "savings_preservation_ratio",
        "emergency_fund_preservation_ratio",
    ],
)
@pytest.mark.parametrize(
    "invalid_ratio",
    [-0.1, 1.1],
)
def test_invalid_preservation_ratio_is_rejected(
    field_name,
    invalid_ratio,
):
    kwargs = {
        "monthly_income_manwon": 300,
        "savings_preservation_ratio": 1.0,
        "emergency_fund_preservation_ratio": 1.0,
    }

    kwargs[field_name] = invalid_ratio

    with pytest.raises(ValueError):
        calculate_affordable_housing_budget_manwon(
            **kwargs
        )
