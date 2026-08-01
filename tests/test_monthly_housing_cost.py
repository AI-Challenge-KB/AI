import pytest

from ai_engine.calculators.monthly_housing_cost import (
    calculate_total_monthly_housing_cost_manwon,
)


def test_basic_monthly_rent_cost():
    result = (
        calculate_total_monthly_housing_cost_manwon(
            monthly_rent_manwon=40,
            management_fee_manwon=8,
            utilities_manwon=7,
            annual_opportunity_cost_rate=0,
        )
    )

    assert result["monthly_rent_manwon"] == 40
    assert result["management_fee_manwon"] == 8
    assert result["utilities_manwon"] == 7
    assert result["net_monthly_cost_manwon"] == 55


def test_jeonse_without_loan():
    result = (
        calculate_total_monthly_housing_cost_manwon(
            monthly_rent_manwon=0,
            management_fee_manwon=8,
            utilities_manwon=7,
            annual_opportunity_cost_rate=0,
        )
    )

    assert result["net_monthly_cost_manwon"] == 15


def test_loan_interest_is_included():
    result = (
        calculate_total_monthly_housing_cost_manwon(
            monthly_rent_manwon=0,
            management_fee_manwon=0,
            utilities_manwon=0,
            loan_principal_manwon=1200,
            annual_loan_interest_rate=3.0,
            annual_opportunity_cost_rate=0,
        )
    )

    assert result["loan_interest_manwon"] == 3
    assert result["net_monthly_cost_manwon"] == 3


def test_deposit_opportunity_cost_is_included():
    result = (
        calculate_total_monthly_housing_cost_manwon(
            monthly_rent_manwon=0,
            management_fee_manwon=0,
            utilities_manwon=0,
            own_cash_deposit_manwon=2000,
            annual_opportunity_cost_rate=2.5,
        )
    )

    assert (
        result[
            "deposit_opportunity_cost_manwon"
        ]
        == 4.17
    )

    assert result["net_monthly_cost_manwon"] == 4.17


def test_full_monthly_cost_scenario():
    result = (
        calculate_total_monthly_housing_cost_manwon(
            monthly_rent_manwon=40,
            management_fee_manwon=8,
            utilities_manwon=7,
            loan_principal_manwon=1200,
            annual_loan_interest_rate=3.0,
            own_cash_deposit_manwon=2000,
            annual_opportunity_cost_rate=2.5,
            commute_cost_change_manwon=2,
            monthly_support_manwon=5,
        )
    )

    assert result["loan_interest_manwon"] == 3
    assert (
        result[
            "deposit_opportunity_cost_manwon"
        ]
        == 4.17
    )

    assert result["gross_monthly_cost_manwon"] == 64.17
    assert result["net_monthly_cost_manwon"] == 59.17


def test_policy_support_reduces_monthly_cost():
    result = (
        calculate_total_monthly_housing_cost_manwon(
            monthly_rent_manwon=50,
            management_fee_manwon=8,
            utilities_manwon=7,
            monthly_support_manwon=20,
            annual_opportunity_cost_rate=0,
        )
    )

    assert result["gross_monthly_cost_manwon"] == 65
    assert result["net_monthly_cost_manwon"] == 45


def test_monthly_cost_cannot_be_negative_after_support():
    result = (
        calculate_total_monthly_housing_cost_manwon(
            monthly_rent_manwon=10,
            management_fee_manwon=0,
            utilities_manwon=0,
            monthly_support_manwon=20,
            annual_opportunity_cost_rate=0,
        )
    )

    assert result["net_monthly_cost_manwon"] == 0


def test_positive_commute_cost_is_added():
    result = (
        calculate_total_monthly_housing_cost_manwon(
            monthly_rent_manwon=40,
            management_fee_manwon=0,
            utilities_manwon=0,
            commute_cost_change_manwon=5,
            annual_opportunity_cost_rate=0,
        )
    )

    assert result["net_monthly_cost_manwon"] == 45


def test_negative_commute_cost_is_allowed():
    result = (
        calculate_total_monthly_housing_cost_manwon(
            monthly_rent_manwon=40,
            management_fee_manwon=0,
            utilities_manwon=0,
            commute_cost_change_manwon=-5,
            annual_opportunity_cost_rate=0,
        )
    )

    assert result["net_monthly_cost_manwon"] == 35


@pytest.mark.parametrize(
    "field_name",
    [
        "monthly_rent_manwon",
        "management_fee_manwon",
        "utilities_manwon",
        "loan_principal_manwon",
        "own_cash_deposit_manwon",
        "monthly_support_manwon",
    ],
)
def test_negative_non_negative_fields_are_rejected(
    field_name,
):
    kwargs = {
        "monthly_rent_manwon": 40,
        "management_fee_manwon": 8,
        "utilities_manwon": 7,
        "loan_principal_manwon": 0,
        "own_cash_deposit_manwon": 0,
        "monthly_support_manwon": 0,
        "annual_opportunity_cost_rate": 0,
    }

    kwargs[field_name] = -1

    with pytest.raises(ValueError):
        calculate_total_monthly_housing_cost_manwon(
            **kwargs
        )


def test_negative_loan_interest_rate_is_rejected():
    with pytest.raises(ValueError):
        calculate_total_monthly_housing_cost_manwon(
            monthly_rent_manwon=40,
            management_fee_manwon=8,
            utilities_manwon=7,
            annual_loan_interest_rate=-1,
        )


def test_negative_opportunity_cost_rate_is_rejected():
    with pytest.raises(ValueError):
        calculate_total_monthly_housing_cost_manwon(
            monthly_rent_manwon=40,
            management_fee_manwon=8,
            utilities_manwon=7,
            annual_opportunity_cost_rate=-1,
        )

def test_precomputed_loan_interest_is_used():
    result = (
        calculate_total_monthly_housing_cost_manwon(
            monthly_rent_manwon=40,
            management_fee_manwon=8,
            utilities_manwon=7,
            loan_principal_manwon=1200,
            annual_loan_interest_rate=10.0,
            precomputed_loan_interest_manwon=3.5,
            annual_opportunity_cost_rate=0,
        )
    )

    # principal/rate로 재계산하지 않고
    # finance matcher가 계산한 3.5만원을 그대로 사용
    assert result["loan_interest_manwon"] == 3.5
    assert result["net_monthly_cost_manwon"] == 58.5


def test_negative_precomputed_loan_interest_is_rejected():
    with pytest.raises(ValueError):
        calculate_total_monthly_housing_cost_manwon(
            monthly_rent_manwon=40,
            management_fee_manwon=8,
            utilities_manwon=7,
            precomputed_loan_interest_manwon=-1,
        )