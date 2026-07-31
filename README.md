# KB 깨비핏 AI

서울 청년의 소득·생활비·부채·보유자금·주거 선호를 바탕으로 감당 가능한 주거비를 계산하고, 최근 전월세 실거래 가격대와 금융상품 조건을 함께 고려해 주거 플랜을 추천하는 AI 엔진입니다.

## 주요 기능

- 감당 가능한 월 주거비 계산
- 서울 25개 자치구 전월세 실거래 가격대 비교
- 월세·전세·주택 유형·면적 조건 기반 후보 필터링
- 보증금 가용자금, 이사 초기비용, 비상예비금 계산
- 청년 전월세 금융상품 사전 매칭
- 예상 대출액 및 월 이자 계산
- 금리 2%p 상승 스트레스 테스트
- 이사 후 유동자금 및 12개월 자산 시뮬레이션
- FastAPI 기반 추천 API 제공

## 현재 버전

- 추천 엔진: `housing_plan_recommender_v1_2`
- API 버전: `v1`
- 평가 기준일: `2026-07-31`
- 추천 대상 지역: 서울
- 추천 계약 형태: 월세·전세
- 매매 추천: 제외

## 프로젝트 구조

```text
.
├── ai_engine/
│   ├── api/
│   │   ├── app.py
│   │   ├── schemas.py
│   │   └── service.py
│   ├── calculators/
│   ├── finance/
│   │   └── finance_matcher_v1.py
│   └── recommenders/
│       ├── housing_plan_recommender_v1.py
│       ├── housing_plan_recommender_v1_1.py
│       └── housing_plan_recommender_v1_2.py
├── data/
│   └── processed/
│       ├── finance/
│       └── housing/market/
├── examples/
│   └── housing_recommendation_request.json
├── scripts/
├── tests/
├── BACKEND_HANDOFF.md
└── requirements-api.txt
```

## 실행 환경

- Python 3.10 이상
- 금액 단위: `만원`
- 면적 단위: `㎡`

## 설치

    python -m pip install -r requirements-api.txt

## 테스트

전체 테스트를 실행합니다.

    python -m pytest -q

현재 기준 정상 결과:

    14 passed

## API 서버 실행

프로젝트 루트에서 실행합니다.

    python -m uvicorn ai_engine.api.app:app \
      --host 127.0.0.1 \
      --port 8000

개발 중 자동 재시작이 필요하면 다음과 같이 실행합니다.

    python -m uvicorn ai_engine.api.app:app \
      --reload \
      --host 127.0.0.1 \
      --port 8000

## API 문서

서버 실행 후 브라우저에서 확인할 수 있습니다.

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## 주요 API

### 상태 확인

    GET /health

응답 예시:

```json
{
  "status": "ok",
  "service": "kb-kkaebifit-recommendation-api",
  "engine_version": "housing_plan_recommender_v1_2"
}
```

### 주거 플랜 추천

    POST /api/v1/housing/recommendations

요청 예시는 다음 파일에 있습니다.

    examples/housing_recommendation_request.json

curl 실행 예시:

    curl -X POST \
      "http://127.0.0.1:8000/api/v1/housing/recommendations" \
      -H "Content-Type: application/json" \
      --data-binary \
      @examples/housing_recommendation_request.json

## 추천 결과의 의미

- `recommended`: 현재 입력 조건에서 추천
- `conditionally_recommended`: 금융상품 적격성 등 추가 확인 필요
- `consider_other_area`: 다른 지역 또는 조건 검토 권장
- `budget_exceeded`: 초기자금 또는 월 주거비 기준 초과

금융상품 매칭 상태:

- `likely_eligible`: 입력된 일반 조건상 주요 기준 충족
- `needs_more_info`: 판단에 필요한 추가 정보 존재
- `ineligible`: 명시적인 조건 불충족

금융상품 결과는 실제 대출 승인 결과가 아닌 사전 추정입니다.

## 운영에 필요한 데이터

추천 엔진 실행을 위해 다음 파일이 필요합니다.

```text
data/processed/housing/market/monthly_rent_market_summary.csv
data/processed/housing/market/jeonse_market_summary.csv
data/processed/finance/loan_product_master.csv
data/processed/finance/loan_eligibility_rules.csv
```

원본 실거래 데이터와 대용량 중간 산출물은 GitHub에 포함하지 않습니다.

## 현재 제한사항

- 실시간 매물이 아닌 최근 실거래 가격대를 추천
- 실제 대중교통 이동시간 API 미연동
- 관리비와 공과금은 입력값 또는 가정값 사용
- 금융상품은 일반 조건 기반 사전 매칭
- 병역기간 연령 특례 미구현
- 신혼·다자녀 소득 특례 미구현
- 대환대출 및 갱신계약 특례 미구현
- 공공임대 실시간 공고 미연동

## 백엔드 연동

백엔드 연동에 필요한 상세 내용은 다음 문서를 참고합니다.

    BACKEND_HANDOFF.md
