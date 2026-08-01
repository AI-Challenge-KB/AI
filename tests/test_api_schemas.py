import pytest
from pydantic import ValidationError

from ai_engine.api.schemas import UserProfileRequest


def make_user_profile(**overrides):
    data = {
        "birth_date": "2000-01-01",
        "monthly_take_home_income_manwon": 250,
        "household_annual_income_manwon": 3000,
        "monthly_living_expense_manwon": 100,
        "monthly_debt_payment_manwon": 0,
        "target_monthly_savings_manwon": 30,
        "housing_funds_manwon": 3000,
    }
    data.update(overrides)
    return UserProfileRequest(**data)


def test_zero_monthly_income_is_allowed():
    profile = make_user_profile(
        monthly_take_home_income_manwon=0,
    )

    assert profile.monthly_take_home_income_manwon == 0


def test_negative_monthly_income_is_rejected():
    with pytest.raises(ValidationError):
        make_user_profile(
            monthly_take_home_income_manwon=-1,
        )


def test_zero_annual_income_is_allowed():
    profile = make_user_profile(
        household_annual_income_manwon=0,
    )

    assert profile.household_annual_income_manwon == 0


def test_negative_annual_income_is_rejected():
    with pytest.raises(ValidationError):
        make_user_profile(
            household_annual_income_manwon=-1,
        )
