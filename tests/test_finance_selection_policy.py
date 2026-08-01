from ai_engine.recommenders.housing_plan_recommender_v1 import (
    HousingPlanRecommenderV1,
    _finance_option_sort_key,
)

from ai_engine.recommenders.housing_plan_recommender_v1_2 import (
    HousingPlanRecommenderV12,
)

def test_optional_likely_finance_has_distinct_confidence():
    finance = {
        "applied": False,
        "match_status": "likely_eligible",
        "selection_reason": (
            "optional_monthly_rent_financing_available"
        ),
    }

    result = (
        HousingPlanRecommenderV12
        ._resolve_finance_decision_confidence(
            finance=finance,
            remaining_deposit_gap=0,
        )
    )

    assert (
        result
        == "optional_prequalified_finance"
    )


def test_optional_needs_info_finance_has_distinct_confidence():
    finance = {
        "applied": False,
        "match_status": "needs_more_info",
        "selection_reason": (
            "optional_monthly_rent_financing_available"
        ),
    }

    result = (
        HousingPlanRecommenderV12
        ._resolve_finance_decision_confidence(
            finance=finance,
            remaining_deposit_gap=0,
        )
    )

    assert (
        result
        == "optional_provisional_finance"
    )


def test_no_finance_needed_confidence():
    finance = {
        "applied": False,
        "match_status": None,
        "selection_reason": (
            "no_finance_needed"
        ),
    }

    result = (
        HousingPlanRecommenderV12
        ._resolve_finance_decision_confidence(
            finance=finance,
            remaining_deposit_gap=0,
        )
    )

    assert result == "no_finance_needed"


def test_no_applicable_finance_confidence():
    finance = {
        "applied": False,
        "match_status": None,
    }

    result = (
        HousingPlanRecommenderV12
        ._resolve_finance_decision_confidence(
            finance=finance,
            remaining_deposit_gap=500,
        )
    )

    assert result == "no_applicable_finance"


def test_applied_likely_finance_is_prequalified():
    finance = {
        "applied": True,
        "match_status": "likely_eligible",
    }

    result = (
        HousingPlanRecommenderV12
        ._resolve_finance_decision_confidence(
            finance=finance,
            remaining_deposit_gap=0,
        )
    )

    assert (
        result
        == "prequalified_estimate"
    )

class DummyFinanceMatcher:
    def __init__(
        self,
        matches,
    ):
        self.matches = matches
        self.call_count = 0

    def match_all(
        self,
        user,
        property_info,
    ):
        self.call_count += 1
        return self.matches


def make_recommender(
    matches,
):
    recommender = (
        HousingPlanRecommenderV1.__new__(
            HousingPlanRecommenderV1
        )
    )

    recommender.finance_matcher = (
        DummyFinanceMatcher(
            matches
        )
    )

    return recommender


def make_deposit_match(
    product_id,
    match_status,
    rate,
    loan,
    remaining_gap=0,
):
    return {
        "product_id": product_id,
        "product_name": product_id,
        "match_status": match_status,
        "missing_fields": [],
        "loan_estimate": {
            "calculation_status": "estimated",
            "estimated_deposit_loan_manwon": loan,
            "remaining_deposit_gap_manwon": (
                remaining_gap
            ),
            "applied_annual_rate_pct": rate,
            "estimated_monthly_interest_manwon": (
                loan * rate / 100 / 12
            ),
        },
    }


def test_likely_eligible_is_prioritized():
    likely = {
        "product_id": "likely",
        "match_status": "likely_eligible",
        "remaining_gap_manwon": 0,
        "monthly_interest_manwon": 3,
        "loan_estimate": {
            "applied_annual_rate_pct": 3.0,
        },
    }

    needs_info = {
        "product_id": "needs_info",
        "match_status": "needs_more_info",
        "remaining_gap_manwon": 0,
        "monthly_interest_manwon": 1,
        "loan_estimate": {
            "applied_annual_rate_pct": 1.0,
        },
    }

    options = [
        needs_info,
        likely,
    ]

    options.sort(
        key=_finance_option_sort_key
    )

    assert (
        options[0]["product_id"]
        == "likely"
    )


def test_no_loan_does_not_call_matcher():
    recommender = make_recommender(
        []
    )

    result = (
        recommender._select_finance_option(
            user={
                "loan_preference": "no_loan"
            },
            property_info={},
            original_gap=1000,
        )
    )

    assert result["applied"] is False
    assert (
        result["selection_reason"]
        == "loan_preference_no_loan"
    )
    assert (
        recommender.finance_matcher
        .call_count
        == 0
    )


def test_minimize_does_not_use_finance_when_no_gap():
    recommender = make_recommender(
        []
    )

    result = (
        recommender._select_finance_option(
            user={
                "loan_preference": "minimize"
            },
            property_info={},
            original_gap=0,
        )
    )

    assert result["applied"] is False
    assert (
        result["selection_reason"]
        == "no_finance_needed"
    )
    assert (
        recommender.finance_matcher
        .call_count
        == 0
    )


def test_likely_eligible_product_wins_in_real_selection():
    matches = [
        make_deposit_match(
            product_id="needs_info",
            match_status="needs_more_info",
            rate=1.0,
            loan=1000,
        ),
        make_deposit_match(
            product_id="likely",
            match_status="likely_eligible",
            rate=3.0,
            loan=1000,
        ),
    ]

    recommender = make_recommender(
        matches
    )

    result = (
        recommender._select_finance_option(
            user={
                "loan_preference": "minimize"
            },
            property_info={},
            original_gap=1000,
        )
    )

    assert result["applied"] is True
    assert (
        result["product_id"]
        == "likely"
    )


def test_available_can_surface_monthly_rent_financing_without_gap():
    matches = [
        {
            "product_id": "monthly_loan",
            "product_name": "월세 금융",
            "match_status": (
                "likely_eligible"
            ),
            "missing_fields": [],
            "loan_estimate": {
                "calculation_status": (
                    "estimated"
                ),
                "estimated_deposit_loan_manwon": 0,
                "remaining_deposit_gap_manwon": 0,
                "estimated_monthly_rent_loan_total_manwon": (
                    600
                ),
                "estimated_monthly_interest_upper_manwon": (
                    1.5
                ),
            },
        }
    ]

    recommender = make_recommender(
        matches
    )

    result = (
        recommender._select_finance_option(
            user={
                "loan_preference": "available"
            },
            property_info={},
            original_gap=0,
        )
    )

    assert result["applied"] is False

    assert (
        result["product_id"]
        == "monthly_loan"
    )

    assert (
        result["selection_reason"]
        == "optional_monthly_rent_financing_available"
    )

    assert (
        result[
            "available_monthly_rent_financing_manwon"
        ]
        == 600
    )

    # 선택 가능한 상품을 안내하지만
    # 실제 추천 비용에는 강제로 적용하지 않는다.
    assert (
        result["estimated_loan_manwon"]
        == 0
    )

    assert (
        result["monthly_interest_manwon"]
        == 0
    )


def test_available_calls_matcher_even_without_gap():
    recommender = make_recommender(
        []
    )

    recommender._select_finance_option(
        user={
            "loan_preference": "available"
        },
        property_info={},
        original_gap=0,
    )

    assert (
        recommender.finance_matcher
        .call_count
        == 1
    )
