from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException

from ai_engine.api.schemas import (
    HealthResponse,
    HousingRecommendationRequest,
    HousingRecommendationResponse,
)
from ai_engine.api.service import (
    create_recommendation_response,
    get_recommender,
)


logger = logging.getLogger(__name__)


app = FastAPI(
    title="KB 깨비핏 Recommendation API",
    description=(
        "서울 청년 전월세 주거 플랜 및 "
        "금융상품 사전 매칭 API"
    ),
    version="1.0.0",
)


@app.on_event("startup")
def load_recommendation_engine() -> None:
    """
    서버 시작 시 데이터 파일과 추천 엔진을 미리 불러와
    첫 요청의 지연시간을 줄인다.
    """
    get_recommender()


@app.get(
    "/health",
    response_model=HealthResponse,
)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=(
            "kb-kkaebifit-recommendation-api"
        ),
        engine_version=(
            "housing_plan_recommender_v1_2"
        ),
    )


@app.post(
    "/api/v1/housing/recommendations",
    response_model=(
        HousingRecommendationResponse
    ),
)
def recommend_housing(
    request: HousingRecommendationRequest,
) -> HousingRecommendationResponse:
    try:
        return create_recommendation_response(
            request
        )

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    except FileNotFoundError as error:
        logger.exception(
            "추천 엔진 데이터 파일 누락"
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "추천 데이터가 준비되지 않았습니다."
            ),
        ) from error

    except Exception as error:
        logger.exception(
            "주거 추천 처리 중 오류"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "주거 추천 처리 중 오류가 발생했습니다."
            ),
        ) from error
