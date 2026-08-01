from ai_engine.api.service import (
    compact_finance,
)


def test_optional_monthly_finance_survives_api_mapping():
    finance = {
        "applied": False,
        "product_id": "monthly_loan",
        "product_name": "청년 월세 금융",
        "match_status": "likely_eligible",
        "decision_confidence": (
            "optional_prequalified_finance"
        ),
        "estimated_loan_manwon": 0,
        "monthly_interest_manwon": 0,
        "remaining_gap_manwon": 0,
        "available_monthly_rent_financing_manwon": (
            600
        ),
        "estimated_monthly_interest_if_used_manwon": (
            1.5
        ),
        "selection_reason": (
            "optional_monthly_rent_financing_available"
        ),
        "missing_fields": [],
        "all_matches": [],
    }

    result = compact_finance(
        finance
    )

    assert result["applied"] is False

    assert (
        result["product_id"]
        == "monthly_loan"
    )

    assert (
        result[
            "available_monthly_rent_financing_manwon"
        ]
        == 600.0
    )

    assert (
        result[
            "estimated_monthly_interest_if_used_manwon"
        ]
        == 1.5
    )

    assert (
        result["selection_reason"]
        == "optional_monthly_rent_financing_available"
    )

    assert (
        result["decision_confidence"]
        == "optional_prequalified_finance"
    )


def test_normal_applied_finance_has_no_optional_amounts():
    finance = {
        "applied": True,
        "product_id": "deposit_loan",
        "product_name": "보증금 대출",
        "match_status": "likely_eligible",
        "decision_confidence": (
            "prequalified_estimate"
        ),
        "estimated_loan_manwon": 1000,
        "monthly_interest_manwon": 2.5,
        "remaining_gap_manwon": 0,
        "missing_fields": [],
        "all_matches": [],
    }

    result = compact_finance(
        finance
    )

    assert result["applied"] is True

    assert (
        result[
            "available_monthly_rent_financing_manwon"
        ]
        is None
    )

    assert (
        result[
            "estimated_monthly_interest_if_used_manwon"
        ]
        is None
    )

    assert (
        result["selection_reason"]
        is None
    )
