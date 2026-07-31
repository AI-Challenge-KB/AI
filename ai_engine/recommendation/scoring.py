from typing import TypedDict


class AffordabilityResult(TypedDict):
    affordable_budget: int
    net_monthly_cost: int
    budget_utilization_ratio: float
    budget_utilization_percent: float
    is_within_budget: bool
    remaining_budget: int
    over_budget_amount: int
    affordability_score: float
    affordability_status: str


def calculate_affordability_score(
    affordable_budget: int,
    net_monthly_cost: int,
) -> float:
    """
    적정 월 주거비 대비 실제 월 주거비의 적정성 점수를 계산한다.

    점수 원칙:
    - 적정 주거비 이내이면 100점
    - 적정 주거비를 초과하면 초과율에 따라 점수를 차감
    - 적정 주거비의 150% 이상이면 0점

    이 점수는 대회 프로토타입의 비교용 지표이며
    공식 금융 심사 기준이 아니다.
    """

    if affordable_budget <= 0:
        return 0.0

    if net_monthly_cost < 0:
        raise ValueError(
            "net_monthly_cost는 0 이상이어야 합니다."
        )

    utilization_ratio = (
        net_monthly_cost / affordable_budget
    )

    if utilization_ratio <= 1.0:
        return 100.0

    score = 100 - (
        (utilization_ratio - 1.0) / 0.5
    ) * 100

    return round(
        max(0.0, min(100.0, score)),
        2,
    )


def determine_affordability_status(
    budget_utilization_ratio: float,
) -> str:
    """
    적정 주거비 대비 사용 비율을 상태값으로 변환한다.
    """

    if budget_utilization_ratio <= 1.0:
        return "within_budget"

    if budget_utilization_ratio <= 1.1:
        return "slightly_over_budget"

    return "over_budget"


def evaluate_affordability(
    affordable_budget: int,
    net_monthly_cost: int,
) -> AffordabilityResult:
    """
    사용자의 적정 월 주거비와 플랜의 월 환산 비용을 비교한다.
    """

    if affordable_budget < 0:
        raise ValueError(
            "affordable_budget은 0 이상이어야 합니다."
        )

    if net_monthly_cost < 0:
        raise ValueError(
            "net_monthly_cost는 0 이상이어야 합니다."
        )

    if affordable_budget == 0:
        utilization_ratio = (
            0.0 if net_monthly_cost == 0 else float("inf")
        )
    else:
        utilization_ratio = (
            net_monthly_cost / affordable_budget
        )

    is_within_budget = (
        net_monthly_cost <= affordable_budget
    )

    remaining_budget = max(
        0,
        affordable_budget - net_monthly_cost,
    )

    over_budget_amount = max(
        0,
        net_monthly_cost - affordable_budget,
    )

    affordability_score = calculate_affordability_score(
        affordable_budget=affordable_budget,
        net_monthly_cost=net_monthly_cost,
    )

    affordability_status = determine_affordability_status(
        utilization_ratio
    )

    utilization_percent = (
        utilization_ratio * 100
        if utilization_ratio != float("inf")
        else float("inf")
    )

    return {
        "affordable_budget": affordable_budget,
        "net_monthly_cost": net_monthly_cost,
        "budget_utilization_ratio": round(
            utilization_ratio,
            4,
        ),
        "budget_utilization_percent": round(
            utilization_percent,
            2,
        ),
        "is_within_budget": is_within_budget,
        "remaining_budget": remaining_budget,
        "over_budget_amount": over_budget_amount,
        "affordability_score": affordability_score,
        "affordability_status": affordability_status,
    }
