from ai_engine.policy.policy_support_matcher_v1 import (
    PolicySupportMatcherV1,
)


def make_matcher():
    return PolicySupportMatcherV1()


def test_d_is_not_available_for_jeonse():
    matcher = make_matcher()

    result = (
        matcher._match_monthly_rent_support(
            user={
                "birth_date": "2000-01-01",
                "evaluation_date": "2026-04-15",
            },
            property_info={
                "contract_type": "jeonse",
                "monthly_rent_manwon": 0,
            },
        )
    )

    assert (
        result["match_status"]
        == "ineligible"
    )

    assert (
        result["currently_applicable"]
        is False
    )

    assert (
        "monthly_rent_contract_required"
        in result["reason_codes"]
    )


def test_d_caps_potential_support_at_20():
    matcher = make_matcher()

    result = (
        matcher._match_monthly_rent_support(
            user={
                "birth_date": "2000-01-01",
                "evaluation_date": "2026-04-15",

                "youth_household_income_eligible": True,
                "origin_household_income_eligible": True,
                "youth_household_assets_eligible": True,
                "origin_household_assets_eligible": True,
            },
            property_info={
                "contract_type": "monthly_rent",
                "monthly_rent_manwon": 60,
            },
        )
    )

    assert (
        result[
            "potential_monthly_support_manwon"
        ]
        == 20.0
    )

    assert (
        result["match_status"]
        == "likely_eligible"
    )

    assert (
        result["application_status"]
        == "open"
    )

    # 승인 전이므로 비용에는 자동 반영하지 않는다.
    assert (
        result[
            "applied_monthly_support_manwon"
        ]
        == 0.0
    )


def test_d_support_does_not_exceed_actual_rent():
    matcher = make_matcher()

    result = (
        matcher._match_monthly_rent_support(
            user={
                "birth_date": "2000-01-01",
                "evaluation_date": "2026-04-15",

                "youth_household_income_eligible": True,
                "origin_household_income_eligible": True,
                "youth_household_assets_eligible": True,
                "origin_household_assets_eligible": True,
            },
            property_info={
                "contract_type": "monthly_rent",
                "monthly_rent_manwon": 15,
            },
        )
    )

    assert (
        result[
            "potential_monthly_support_manwon"
        ]
        == 15.0
    )


def test_d_current_2026_cycle_is_closed_after_may():
    matcher = make_matcher()

    result = (
        matcher._match_monthly_rent_support(
            user={
                "birth_date": "2000-01-01",
                "evaluation_date": "2026-08-02",

                "youth_household_income_eligible": True,
                "origin_household_income_eligible": True,
                "youth_household_assets_eligible": True,
                "origin_household_assets_eligible": True,
            },
            property_info={
                "contract_type": "monthly_rent",
                "monthly_rent_manwon": 50,
            },
        )
    )

    assert (
        result["match_status"]
        == "likely_eligible"
    )

    assert (
        result["application_status"]
        == "closed"
    )

    assert (
        result["currently_applicable"]
        is False
    )

    assert (
        result[
            "applied_monthly_support_manwon"
        ]
        == 0.0
    )


def test_d_missing_income_asset_information_is_not_guessed():
    matcher = make_matcher()

    result = (
        matcher._match_monthly_rent_support(
            user={
                "birth_date": "2000-01-01",
                "evaluation_date": "2026-04-15",
            },
            property_info={
                "contract_type": "monthly_rent",
                "monthly_rent_manwon": 50,
            },
        )
    )

    assert (
        result["match_status"]
        == "needs_more_info"
    )

    assert (
        len(result["missing_fields"])
        == 4
    )


def test_d_failed_asset_condition_is_ineligible():
    matcher = make_matcher()

    result = (
        matcher._match_monthly_rent_support(
            user={
                "birth_date": "2000-01-01",
                "evaluation_date": "2026-04-15",

                "youth_household_income_eligible": True,
                "origin_household_income_eligible": True,
                "youth_household_assets_eligible": False,
                "origin_household_assets_eligible": True,
            },
            property_info={
                "contract_type": "monthly_rent",
                "monthly_rent_manwon": 50,
            },
        )
    )

    assert (
        result["match_status"]
        == "ineligible"
    )


def test_e_does_not_affect_current_housing_cost():
    matcher = make_matcher()

    result = (
        matcher._match_housing_dream_savings(
            user={
                "birth_date": "2000-01-01",
                "evaluation_date": "2026-08-02",
                "is_no_home": True,
                "individual_annual_income_manwon": 4000,
            }
        )
    )

    assert (
        result["match_status"]
        == "likely_eligible"
    )

    assert (
        result["used_in_cost_scenario"]
        is False
    )

    assert (
        result["affects_deposit_gap"]
        is False
    )

    assert (
        result[
            "applied_monthly_support_manwon"
        ]
        == 0.0
    )


def test_e_requires_individual_income():
    matcher = make_matcher()

    result = (
        matcher._match_housing_dream_savings(
            user={
                "birth_date": "2000-01-01",
                "evaluation_date": "2026-08-02",
                "is_no_home": True,

                # household income만 존재해도
                # 개인 연소득으로 대신 사용하지 않는다.
                "household_annual_income_manwon": 4000,
            }
        )
    )

    assert (
        result["match_status"]
        == "needs_more_info"
    )

    assert (
        "individual_annual_income_manwon"
        in result["missing_fields"]
    )


def test_e_income_over_limit_is_ineligible():
    matcher = make_matcher()

    result = (
        matcher._match_housing_dream_savings(
            user={
                "birth_date": "2000-01-01",
                "evaluation_date": "2026-08-02",
                "is_no_home": True,
                "individual_annual_income_manwon": 5500,
            }
        )
    )

    assert (
        result["match_status"]
        == "ineligible"
    )


def test_match_all_returns_d_and_e_separately():
    matcher = make_matcher()

    results = matcher.match_all(
        user={
            "birth_date": "2000-01-01",
            "evaluation_date": "2026-08-02",
            "is_no_home": True,
        },
        property_info={
            "contract_type": "monthly_rent",
            "monthly_rent_manwon": 50,
        },
    )

    assert len(results) == 2

    assert {
        result["support_code"]
        for result in results
    } == {
        "D",
        "E",
    }
