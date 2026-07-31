from ai_engine.schemas.policy import HousingPolicy
from ai_engine.schemas.user_profile import UserProfile


def evaluate_policy_eligibility(
    profile: UserProfile,
    policy: HousingPolicy,
) -> dict:
    reasons: list[str] = []
    needs_review: list[str] = []

    if policy.age_min is not None and profile.age < policy.age_min:
        reasons.append("최소 연령 조건을 충족하지 않습니다.")

    if policy.age_max is not None and profile.age > policy.age_max:
        reasons.append("최대 연령 조건을 충족하지 않습니다.")

    if policy.homeless_required and not profile.is_homeless:
        reasons.append("무주택 조건을 충족하지 않습니다.")

    if (
        policy.target_region_code is not None
        and policy.target_region_code not in profile.desired_region
    ):
        needs_review.append("지역 조건의 추가 확인이 필요합니다.")

    if reasons:
        status = "ineligible"
    elif needs_review:
        status = "needs_review"
    else:
        status = "eligible"

    return {
        "policy_id": policy.policy_id,
        "policy_name": policy.policy_name,
        "status": status,
        "reasons": reasons,
        "needs_review": needs_review,
    }