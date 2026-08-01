from ai_engine.schemas.housing_plan import HousingPlan


WON_PER_MANWON = 10_000

DEFAULT_OPPORTUNITY_COST_RATE_PCT = 2.5


def calculate_monthly_interest(
    principal: int,
    annual_interest_rate: float,
) -> int:
    """
    원금과 연이율을 이용하여 월 이자를 계산한다.

    Args:
        principal:
            대출 원금 또는 보증금.
            단위는 원.

        annual_interest_rate:
            연이율.
            예를 들어 연 3.5%라면 3.5를 입력한다.

    Returns:
        원 단위로 반올림한 월 이자.
    """

    if principal < 0:
        raise ValueError(
            "principal은 0 이상이어야 합니다."
        )

    if annual_interest_rate < 0:
        raise ValueError(
            "annual_interest_rate는 "
            "0 이상이어야 합니다."
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
    loan_interest_override: int | None = None,
    deposit: int = 0,
    annual_opportunity_cost_rate: float = 0.0,
    commute_cost_change: int = 0,
    monthly_support: int = 0,
) -> dict[str, int]:
    """
    원 단위 월 환산 총주거비 계산 함수.

    총 월 주거비 =
        월세
        + 관리비
        + 공과금
        + 대출 월 이자
        + 자기자금 보증금 기회비용
        + 통근비 변화
        - 월 환산 정책지원금

    기본적으로 대출 원금과 연이율을 이용해
    월 대출이자를 계산한다.

    단, FinanceMatcher 등 외부 로직에서
    상품별 특수 금리 구조를 이미 반영하여
    월 이자를 계산했다면
    loan_interest_override를 전달할 수 있다.

    이 경우 loan_interest_override를 우선 사용한다.

    Args:
        monthly_rent:
            월세. 단위는 원.

        management_fee:
            관리비. 단위는 원.

        utilities:
            예상 공과금. 단위는 원.

        loan_principal:
            주거 관련 대출 원금.
            단위는 원.

        annual_loan_interest_rate:
            대출 연이율.
            예: 3.5%라면 3.5.

        loan_interest_override:
            이미 계산된 월 대출이자.
            단위는 원.

            값이 주어지면
            loan_principal과 annual_loan_interest_rate를
            이용해 이자를 다시 계산하지 않는다.

        deposit:
            사용자가 실제 자기자금으로
            투입하는 보증금.
            단위는 원.

        annual_opportunity_cost_rate:
            자기자금 보증금의 연 기회비용률.
            예: 2.5%라면 2.5.

        commute_cost_change:
            현재 거주지 대비 월 통근비 증감액.
            단위는 원.

            비용 증가이면 양수,
            비용 감소이면 음수.

        monthly_support:
            월세지원, 이자지원 등
            월 환산 정책지원 합계.
            단위는 원.

    Returns:
        월 주거비 세부 항목과
        gross/net 월 주거비를 담은 딕셔너리.
    """

    non_negative_values = {
        "monthly_rent": monthly_rent,
        "management_fee": management_fee,
        "utilities": utilities,
        "loan_principal": loan_principal,
        "deposit": deposit,
        "monthly_support": monthly_support,
    }

    for field_name, value in (
        non_negative_values.items()
    ):
        if value < 0:
            raise ValueError(
                f"{field_name}은 "
                "0 이상이어야 합니다."
            )

    if annual_loan_interest_rate < 0:
        raise ValueError(
            "annual_loan_interest_rate는 "
            "0 이상이어야 합니다."
        )

    if annual_opportunity_cost_rate < 0:
        raise ValueError(
            "annual_opportunity_cost_rate는 "
            "0 이상이어야 합니다."
        )

    if loan_interest_override is not None:
        if loan_interest_override < 0:
            raise ValueError(
                "loan_interest_override는 "
                "0 이상이어야 합니다."
            )

        loan_interest = (
            loan_interest_override
        )

    else:
        loan_interest = (
            calculate_monthly_interest(
                principal=loan_principal,
                annual_interest_rate=(
                    annual_loan_interest_rate
                ),
            )
        )

    deposit_opportunity_cost = (
        calculate_monthly_interest(
            principal=deposit,
            annual_interest_rate=(
                annual_opportunity_cost_rate
            ),
        )
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
        gross_monthly_cost
        - monthly_support,
    )

    return {
        "monthly_rent": monthly_rent,
        "management_fee": management_fee,
        "utilities": utilities,
        "loan_interest": loan_interest,
        "deposit_opportunity_cost": (
            deposit_opportunity_cost
        ),
        "commute_cost_change": (
            commute_cost_change
        ),
        "monthly_support": monthly_support,
        "gross_monthly_cost": (
            gross_monthly_cost
        ),
        "net_monthly_cost": (
            net_monthly_cost
        ),
    }


def calculate_total_monthly_housing_cost_manwon(
    monthly_rent_manwon: float,
    management_fee_manwon: float,
    utilities_manwon: float,
    loan_principal_manwon: float = 0.0,
    annual_loan_interest_rate: float = 0.0,
    precomputed_loan_interest_manwon: (
        float | None
    ) = None,
    own_cash_deposit_manwon: float = 0.0,
    annual_opportunity_cost_rate: float = (
        DEFAULT_OPPORTUNITY_COST_RATE_PCT
    ),
    commute_cost_change_manwon: float = 0.0,
    monthly_support_manwon: float = 0.0,
) -> dict[str, float]:
    """
    추천 API에서 사용하는
    만원 단위 월 환산 총주거비 계산 함수.

    추천 엔진에서 사용하는 월 주거비 계산의
    Single Source of Truth.

    모든 금액 입력과 반환 단위는 만원이다.

    총 월 주거비 =
        월세
        + 관리비
        + 공과금
        + 대출 월 이자
        + 자기자금 보증금 기회비용
        + 통근비 변화
        - 월 환산 정책지원금

    FinanceMatcher에서 상품별 금리 구조를 반영해
    월 이자를 이미 계산한 경우
    precomputed_loan_interest_manwon을 전달한다.

    이 경우 해당 값을 그대로 사용하며
    대출이자를 다시 계산하지 않는다.

    own_cash_deposit_manwon은
    전체 보증금이 아니라 실제 자기자금으로
    투입하는 보증금이다.
    """

    def manwon_to_won(
        value: float,
    ) -> int:
        return round(
            float(value)
            * WON_PER_MANWON
        )

    def won_to_manwon(
        value: int,
    ) -> float:
        return round(
            value
            / WON_PER_MANWON,
            2,
        )

    loan_interest_override = None

    if (
        precomputed_loan_interest_manwon
        is not None
    ):
        loan_interest_override = (
            manwon_to_won(
                precomputed_loan_interest_manwon
            )
        )

    result = (
        calculate_total_monthly_housing_cost(
            monthly_rent=manwon_to_won(
                monthly_rent_manwon
            ),
            management_fee=manwon_to_won(
                management_fee_manwon
            ),
            utilities=manwon_to_won(
                utilities_manwon
            ),
            loan_principal=manwon_to_won(
                loan_principal_manwon
            ),
            annual_loan_interest_rate=(
                annual_loan_interest_rate
            ),
            loan_interest_override=(
                loan_interest_override
            ),
            deposit=manwon_to_won(
                own_cash_deposit_manwon
            ),
            annual_opportunity_cost_rate=(
                annual_opportunity_cost_rate
            ),
            commute_cost_change=manwon_to_won(
                commute_cost_change_manwon
            ),
            monthly_support=manwon_to_won(
                monthly_support_manwon
            ),
        )
    )

    return {
        "monthly_rent_manwon": (
            won_to_manwon(
                result[
                    "monthly_rent"
                ]
            )
        ),
        "management_fee_manwon": (
            won_to_manwon(
                result[
                    "management_fee"
                ]
            )
        ),
        "utilities_manwon": (
            won_to_manwon(
                result[
                    "utilities"
                ]
            )
        ),
        "loan_interest_manwon": (
            won_to_manwon(
                result[
                    "loan_interest"
                ]
            )
        ),
        "deposit_opportunity_cost_manwon": (
            won_to_manwon(
                result[
                    "deposit_opportunity_cost"
                ]
            )
        ),
        "commute_cost_change_manwon": (
            won_to_manwon(
                result[
                    "commute_cost_change"
                ]
            )
        ),
        "monthly_support_manwon": (
            won_to_manwon(
                result[
                    "monthly_support"
                ]
            )
        ),
        "gross_monthly_cost_manwon": (
            won_to_manwon(
                result[
                    "gross_monthly_cost"
                ]
            )
        ),
        "net_monthly_cost_manwon": (
            won_to_manwon(
                result[
                    "net_monthly_cost"
                ]
            )
        ),
    }


def calculate_housing_plan_cost(
    plan: HousingPlan,
    annual_opportunity_cost_rate: float = (
        DEFAULT_OPPORTUNITY_COST_RATE_PCT
    ),
) -> dict[str, int | float | str | None]:
    """
    HousingPlan 객체를 받아
    월 환산 총주거비를 계산한다.

    기존 원 단위 계산 함수를 재사용하여
    월세, 전세, 공공임대 플랜을
    같은 기준으로 계산한다.

    HousingPlan의 deposit이 전체 보증금이고
    loan_amount가 보증금 관련 대출액이라고 보고,
    기회비용에는 실제 자기자금 투입분만 반영한다.

    Args:
        plan:
            계산할 HousingPlan 객체.

        annual_opportunity_cost_rate:
            자기자금 보증금에 적용할
            연 기회비용률.

            기본값은 MVP 가정값인 2.5%.

    Returns:
        주거 플랜 정보와
        월 환산 비용 결과가 합쳐진 딕셔너리.
    """

    total_monthly_support = (
        plan.monthly_policy_support
        + plan.monthly_interest_support
    )

    own_cash_deposit = max(
        0,
        plan.deposit
        - plan.loan_amount,
    )

    cost_result = (
        calculate_total_monthly_housing_cost(
            monthly_rent=plan.monthly_rent,
            management_fee=(
                plan.management_fee
            ),
            utilities=plan.utilities,
            loan_principal=(
                plan.loan_amount
            ),
            annual_loan_interest_rate=(
                plan.annual_interest_rate
            ),
            deposit=own_cash_deposit,
            annual_opportunity_cost_rate=(
                annual_opportunity_cost_rate
            ),
            commute_cost_change=(
                plan.commute_cost_change
            ),
            monthly_support=(
                total_monthly_support
            ),
        )
    )

    return {
        "plan_id": plan.plan_id,
        "plan_name": plan.plan_name,
        "plan_type": plan.plan_type,
        "region_code": plan.region_code,
        "region_name": plan.region_name,
        "deposit": plan.deposit,
        "own_cash_deposit": (
            own_cash_deposit
        ),
        "loan_amount": plan.loan_amount,
        "annual_interest_rate": (
            plan.annual_interest_rate
        ),
        "monthly_policy_support": (
            plan.monthly_policy_support
        ),
        "monthly_interest_support": (
            plan.monthly_interest_support
        ),
        "commute_minutes": (
            plan.commute_minutes
        ),
        "contract_safety_score": (
            plan.contract_safety_score
        ),
        **cost_result,
    }