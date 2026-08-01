from ai_engine.recommenders.housing_plan_recommender_v1 import (
    HousingPlanRecommenderV1,
)


class DummyRecommender(HousingPlanRecommenderV1):
    def __init__(self):
        pass

    def _select_finance_option(
        self,
        user,
        property_info,
        original_gap,
    ):
        return {
            "applied": False,
            "product_id": None,
            "product_name": None,
            "match_status": None,
            "estimated_loan_manwon": 0.0,
            "monthly_interest_manwon": 0.0,
            "remaining_gap_manwon": original_gap,
            "missing_fields": [],
            "all_matches": [],
        }


class DummyFinanceRecommender(
    HousingPlanRecommenderV1
):
    def __init__(self):
        pass

    def _select_finance_option(
        self,
        user,
        property_info,
        original_gap,
    ):
        return {
            "applied": True,
            "product_id": "test_loan",
            "product_name": "테스트 대출",
            "match_status": "likely_eligible",
            "estimated_loan_manwon": 700.0,
            "monthly_interest_manwon": 2.0,
            "remaining_gap_manwon": 0.0,
            "missing_fields": [],
            "all_matches": [],
        }


def make_row():
    return {
        "deposit_median_manwon": 1200.0,
        "monthly_rent_median_manwon": 40.0,
        "market_area_bucket": "20_30",
        "front_area_bucket": "20_30",
        "housing_type": "row_house",
        "district_name": "영등포구",
        "district_code": "11560",
        "deposit_bucket": "1000_3000",
        "deposit_bucket_label": "1,000만~3,000만원",
        "confidence": "high",
        "contract_count": 100,
    }


def make_user(
    available_cash=2000,
):
    return {
        "housing_funds_manwon": available_cash,
        "deposit_allocable_cash_manwon": (
            available_cash
        ),
        "management_fee_assumption_manwon": 8,
        "utilities_assumption_manwon": 7,
        "monthly_take_home_income_manwon": 300,
        "monthly_living_expense_manwon": 100,
        "monthly_debt_payment_manwon": 0,
        "target_monthly_savings_manwon": 50,
    }


def test_candidate_uses_deposit_opportunity_cost():
    recommender = DummyRecommender()

    candidate = recommender._build_candidate(
        transaction_type="monthly_rent",
        row=make_row(),
        user=make_user(2000),
        affordable_budget=130,
    )

    # 자기자금 보증금 1,200만원
    # 1,200 * 2.5% / 12 = 2.5만원
    assert (
        candidate["monthly_cost"][
            "deposit_opportunity_cost_manwon"
        ]
        == 2.5
    )

    # 40 + 8 + 7 + 2.5
    assert (
        candidate["monthly_cost"][
            "total_monthly_housing_cost_manwon"
        ]
        == 57.5
    )


def test_candidate_uses_finance_matcher_interest():
    recommender = DummyFinanceRecommender()

    candidate = recommender._build_candidate(
        transaction_type="monthly_rent",
        row=make_row(),
        user=make_user(500),
        affordable_budget=130,
    )

    # 보증금 1,200 - 대출 700 = 자기자금 500
    assert (
        candidate["monthly_cost"][
            "own_cash_deposit_manwon"
        ]
        == 500
    )

    # FinanceMatcher가 계산한 월 이자 2만원을 그대로 사용
    assert (
        candidate["monthly_cost"][
            "loan_interest_manwon"
        ]
        == 2.0
    )

    # 자기자금 보증금 기회비용
    # 500 * 2.5% / 12 ≈ 1.04만원
    assert (
        candidate["monthly_cost"][
            "deposit_opportunity_cost_manwon"
        ]
        == 1.04
    )

    # 40 + 8 + 7 + 2 + 1.04
    assert (
        candidate["monthly_cost"][
            "total_monthly_housing_cost_manwon"
        ]
        == 58.04
    )
def test_rough_monthly_cost_uses_opportunity_cost():
    row = {
        "deposit_median_manwon": 1200.0,
        "monthly_rent_median_manwon": 40.0,
    }

    cost = (
        HousingPlanRecommenderV1
        ._calculate_pre_finance_monthly_cost(
            transaction_type="monthly_rent",
            row=row,
            available_cash=2000,
            management_fee=8,
            utilities=7,
        )
    )

    # 자기자금 1,200만원
    # 기회비용 = 1,200 * 2.5% / 12 = 2.5만원
    # 40 + 8 + 7 + 2.5
    assert cost == 57.5


def test_rough_monthly_cost_uses_only_allocable_cash():
    row = {
        "deposit_median_manwon": 1200.0,
        "monthly_rent_median_manwon": 40.0,
    }

    cost = (
        HousingPlanRecommenderV1
        ._calculate_pre_finance_monthly_cost(
            transaction_type="monthly_rent",
            row=row,
            available_cash=500,
            management_fee=8,
            utilities=7,
        )
    )

    # 보증금은 1,200만원이지만
    # 실제 자기자금 가용액은 500만원.
    # 기회비용 = 약 1.04만원
    assert cost == 56.04


def test_rough_jeonse_cost_uses_same_calculator():
    row = {
        "deposit_median_manwon": 1200.0,
    }

    cost = (
        HousingPlanRecommenderV1
        ._calculate_pre_finance_monthly_cost(
            transaction_type="jeonse",
            row=row,
            available_cash=2000,
            management_fee=8,
            utilities=7,
        )
    )

    # 전세이므로 월세 0
    # 8 + 7 + 보증금 기회비용 2.5
    assert cost == 17.5