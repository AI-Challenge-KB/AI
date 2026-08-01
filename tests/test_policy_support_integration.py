from ai_engine.recommenders.housing_plan_recommender_v1 import (
    HousingPlanRecommenderV1,
)

def test_candidate_payload_keeps_policy_supports():
    policy_supports = [
        {
            "support_code": "D",
        },
        {
            "support_code": "E",
        },
    ]

    candidate = {
        "policy_supports": (
            policy_supports
        ),
    }

    assert (
        candidate["policy_supports"]
        == policy_supports
    )

    assert {
        support["support_code"]
        for support
        in candidate["policy_supports"]
    } == {
        "D",
        "E",
    }

def test_policy_support_matcher_is_lazy_initialized():
    recommender = (
        HousingPlanRecommenderV1.__new__(
            HousingPlanRecommenderV1
        )
    )

    matcher = (
        recommender
        ._get_policy_support_matcher()
    )

    assert matcher is not None

    assert (
        recommender.policy_support_matcher
        is matcher
    )


def test_monthly_candidate_gets_d_and_e_supports():
    recommender = (
        HousingPlanRecommenderV1.__new__(
            HousingPlanRecommenderV1
        )
    )

    matcher = (
        recommender
        ._get_policy_support_matcher()
    )

    supports = matcher.match_all(
        user={
            "birth_date": "2000-01-01",
            "evaluation_date": "2026-08-02",
            "is_no_home": True,
        },
        property_info={
            "contract_type": (
                "monthly_rent"
            ),
            "housing_type": (
                "officetel"
            ),
            "deposit_manwon": 1000,
            "monthly_rent_manwon": 50,
            "area_m2": 30,
        },
    )

    assert {
        support["support_code"]
        for support in supports
    } == {
        "D",
        "E",
    }


def test_policy_support_is_not_used_in_cost_scenario():
    recommender = (
        HousingPlanRecommenderV1.__new__(
            HousingPlanRecommenderV1
        )
    )

    supports = (
        recommender
        ._get_policy_support_matcher()
        .match_all(
            user={
                "birth_date": "2000-01-01",
                "evaluation_date": "2026-08-02",
                "is_no_home": True,
            },
            property_info={
                "contract_type": (
                    "monthly_rent"
                ),
                "monthly_rent_manwon": 50,
            },
        )
    )

    for support in supports:
        assert (
            support[
                "used_in_cost_scenario"
            ]
            is False
        )

        assert (
            support[
                "applied_monthly_support_manwon"
            ]
            == 0.0
        )


def test_jeonse_d_is_ineligible_but_e_remains_separate():
    recommender = (
        HousingPlanRecommenderV1.__new__(
            HousingPlanRecommenderV1
        )
    )

    supports = (
        recommender
        ._get_policy_support_matcher()
        .match_all(
            user={
                "birth_date": "2000-01-01",
                "evaluation_date": "2026-08-02",
                "is_no_home": True,
            },
            property_info={
                "contract_type": "jeonse",
                "monthly_rent_manwon": 0,
            },
        )
    )

    support_map = {
        support["support_code"]:
        support
        for support in supports
    }

    assert (
        support_map["D"][
            "match_status"
        ]
        == "ineligible"
    )

    assert (
        support_map["E"][
            "support_type"
        ]
        == "long_term_savings"
    )
