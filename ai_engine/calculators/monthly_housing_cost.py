from ai_engine.schemas.housing_plan import HousingPlan


def calculate_monthly_interest(
    principal: int,
    annual_interest_rate: float,
) -> int:
    """
    원금과 연이율을 이용하여 월 이자를 계산한다.

    Args:
        principal:
            대출 원금 또는 보증금. 단위는 원.
        annual_interest_rate:
            연이율. 예를 들어 연 3.5%라면 3.5를 입력한다.

    Returns:
        원 단위로 반올림한 월 이자.
    """

    if principal < 0:
        raise ValueError("principal은 0 이상이어야 합니다.")

    if annual_interest_rate < 0:
        raise ValueError(
            "annual_interest_rate는 0 이상이어야 합니다."
        )

    monthly_interest = (
        principal
        * (annual_interest_rate / 100)
        / 12
    )

    return round(monthly_interest)


def calculate_total_monthly_housing_cost(
    monthly_rent: int,
    management_fee: int,
    utilities: int,
    loan_principal: int = 0,
    annual_loan_interest_rate: float = 0.0,
    deposit: int = 0,
    annual_opportunity_cost_rate: float = 0.0,
    commute_cost_change: int = 0,
    monthly_support: int = 0,
) -> dict[str, int]:
    """
    하나의 주거 후보에 대한 월 환산 총주거비를 계산한다.

    총주거비에는 월세, 관리비, 공과금, 대출이자,
    보증금 기회비용, 통근비 변화를 포함한다.

    정책지원금과 이자지원금은 monthly_support에 합산하여
    전달하며 최종 월 부담에서 차감한다.

    Args:
        monthly_rent:
            월세. 단위는 원.
        management_fee:
            월 관리비. 단위는 원.
        utilities:
            월 예상 공과금. 단위는 원.
        loan_principal:
            주거 관련 대출 원금. 단위는 원.
        annual_loan_interest_rate:
            대출 연이율. 예: 3.5%라면 3.5.
        deposit:
            사용자가 실제로 투입하는 자기자금 보증금.
            단위는 원.
        annual_opportunity_cost_rate:
            보증금에 적용할 연 기회비용률.
            예: 2.5%라면 2.5.
        commute_cost_change:
            현재 거주지 대비 월 통근비 증감액.
            비용 증가이면 양수, 감소이면 음수.
        monthly_support:
            월세지원금과 이자지원금 등의 월 환산 합계.
            단위는 원.

    Returns:
        세부 비용과 최종 월 환산 총주거비가 담긴 딕셔너리.
    """

    non_negative_values = {
        "monthly_rent": monthly_rent,
        "management_fee": management_fee,
        "utilities": utilities,
        "loan_principal": loan_principal,
        "deposit": deposit,
        "monthly_support": monthly_support,
    }

    for field_name, value in non_negative_values.items():
        if value < 0:
            raise ValueError(
                f"{field_name}은 0 이상이어야 합니다."
            )

    if annual_loan_interest_rate < 0:
        raise ValueError(
            "annual_loan_interest_rate는 0 이상이어야 합니다."
        )

    if annual_opportunity_cost_rate < 0:
        raise ValueError(
            "annual_opportunity_cost_rate는 0 이상이어야 합니다."
        )

    loan_interest = calculate_monthly_interest(
        principal=loan_principal,
        annual_interest_rate=annual_loan_interest_rate,
    )

    deposit_opportunity_cost = calculate_monthly_interest(
        principal=deposit,
        annual_interest_rate=annual_opportunity_cost_rate,
    )

    gross_monthly_cost = (
        monthly_rent
        + management_fee
        + utilities
        + loan_interest
        + deposit_opportunity_cost
        + commute_cost_change
    )

    net_monthly_cost = max(
        0,
        gross_monthly_cost - monthly_support,
    )

    return {
        "monthly_rent": monthly_rent,
        "management_fee": management_fee,
        "utilities": utilities,
        "loan_interest": loan_interest,
        "deposit_opportunity_cost": (
            deposit_opportunity_cost
        ),
        "commute_cost_change": commute_cost_change,
        "monthly_support": monthly_support,
        "gross_monthly_cost": gross_monthly_cost,
        "net_monthly_cost": net_monthly_cost,
    }


def calculate_housing_plan_cost(
    plan: HousingPlan,
    annual_opportunity_cost_rate: float = 2.5,
) -> dict[str, int | float | str | None]:
    """
    HousingPlan 객체를 받아 월 환산 총주거비를 계산한다.

    기존 calculate_total_monthly_housing_cost 함수를 재사용하여
    월세, 전세, 공공임대 플랜을 같은 기준으로 계산한다.

    Args:
        plan:
            계산할 HousingPlan 객체.
        annual_opportunity_cost_rate:
            자기자금 보증금에 적용할 연 기회비용률.
            기본값은 MVP 가정값인 2.5%.

    Returns:
        주거 플랜 정보와 월 환산 비용 결과가 합쳐진 딕셔너리.
    """

    total_monthly_support = (
        plan.monthly_policy_support
        + plan.monthly_interest_support
    )

    cost_result = calculate_total_monthly_housing_cost(
        monthly_rent=plan.monthly_rent,
        management_fee=plan.management_fee,
        utilities=plan.utilities,
        loan_principal=plan.loan_amount,
        annual_loan_interest_rate=(
            plan.annual_interest_rate
        ),
        deposit=plan.deposit,
        annual_opportunity_cost_rate=(
            annual_opportunity_cost_rate
        ),
        commute_cost_change=plan.commute_cost_change,
        monthly_support=total_monthly_support,
    )

    return {
        "plan_id": plan.plan_id,
        "plan_name": plan.plan_name,
        "plan_type": plan.plan_type,
        "region_code": plan.region_code,
        "region_name": plan.region_name,
        "deposit": plan.deposit,
        "loan_amount": plan.loan_amount,
        "annual_interest_rate": plan.annual_interest_rate,
        "monthly_policy_support": (
            plan.monthly_policy_support
        ),
        "monthly_interest_support": (
            plan.monthly_interest_support
        ),
        "commute_minutes": plan.commute_minutes,
        "contract_safety_score": (
            plan.contract_safety_score
        ),
        **cost_result,
    }