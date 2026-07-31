# KB 깨비핏 AI 백엔드 연동 가이드

## 1. 연동 대상

현재 백엔드에서 호출할 API는 두 개입니다.

```text
GET  /health
POST /api/v1/housing/recommendations
```

추천 엔진 버전:

```text
housing_plan_recommender_v1_2
```

## 2. 빠른 실행

저장소를 내려받습니다.

    git clone https://github.com/AI-Challenge-KB/AI.git
    cd AI

패키지를 설치합니다.

    python -m pip install -r requirements-api.txt

테스트를 실행합니다.

    python -m pytest -q

API 서버를 실행합니다.

    python -m uvicorn ai_engine.api.app:app \
      --host 0.0.0.0 \
      --port 8000

정상 실행 여부를 확인합니다.

    curl http://127.0.0.1:8000/health

## 3. 상태 확인 API

### 요청

```http
GET /health
```

### 정상 응답

```json
{
  "status": "ok",
  "service": "kb-kkaebifit-recommendation-api",
  "engine_version": "housing_plan_recommender_v1_2"
}
```

## 4. 주거 추천 API

### 요청

```http
POST /api/v1/housing/recommendations
Content-Type: application/json
```

전체 요청 예시는 다음 파일에 있습니다.

```text
examples/housing_recommendation_request.json
```

### 요청 예시

```json
{
  "request_id": "demo-user-001",
  "user_profile": {
    "birth_date": "2001-03-06",
    "evaluation_date": "2026-07-31",
    "monthly_take_home_income_manwon": 280,
    "household_annual_income_manwon": 3600,
    "monthly_living_expense_manwon": 110,
    "monthly_debt_payment_manwon": 0,
    "target_monthly_savings_manwon": 50,
    "housing_funds_manwon": 3000,
    "is_no_home": true,
    "all_household_members_no_home": true,
    "household_head_status": "prospective_household_head",
    "is_single_household_head": true,
    "passes_fund_asset_test": null
  },
  "housing_preference": {
    "contract_preference": "both",
    "preferred_housing_types": [
      "officetel",
      "row_house"
    ],
    "minimum_area_bucket": "20_30",
    "loan_preference": "minimize",
    "allowed_district_names": null
  },
  "cost_assumptions": {
    "affordable_monthly_housing_cost_manwon": 72,
    "moving_initial_cost_manwon": 100,
    "minimum_cash_reserve_manwon": 300,
    "management_fee_assumption_manwon": 8,
    "utilities_assumption_manwon": 7
  },
  "top_n": 5
}
```

## 5. 입력 필드 규칙

### 금액과 면적

- 모든 금액 단위는 `만원`
- 면적 단위는 `㎡`
- 백엔드에서 원 단위 값을 전달하면 안 됨

### 계약 형태

`contract_preference` 허용값:

```text
monthly_rent
jeonse
both
```

### 주택 유형

`preferred_housing_types` 허용값:

```text
apartment
officetel
row_house
single_multi_house
```

### 최소 면적 구간

`minimum_area_bucket` 허용값:

```text
any
under_20
20_30
30_40
over_40
```

### 대출 선호

`loan_preference` 허용값:

```text
available
minimize
no_loan
```

### 세대주 상태

`household_head_status` 허용값:

```text
household_head
prospective_household_head
household_member
```

## 6. 응답에서 주로 사용할 필드

각 추천 후보는 다음 정보를 포함합니다.

```text
rank
candidate_id
title
district_name
housing_type
transaction_type
area_label
score_total
judgement
market_price
initial_funds
monthly_cost
finance
stress_test
future_simulation
explanations
```

프론트 추천 카드에서 우선 사용할 필드:

```text
title
district_name
housing_type_label
transaction_type_label
area_label
score_total
judgement.label
market_price.deposit_median_manwon
market_price.monthly_rent_median_manwon
monthly_cost.total_monthly_housing_cost_manwon
initial_funds.estimated_loan_manwon
initial_funds.liquid_cash_after_move_manwon
finance.product_name
finance.match_status
explanations.affordability
explanations.initial_funds
explanations.finance
```

## 7. 추천 판단 코드

```text
recommended
conditionally_recommended
consider_other_area
budget_exceeded
```

화면 표시 권장값:

```text
recommended               → 추천
conditionally_recommended → 조건부 추천
consider_other_area       → 다른 지역 검토
budget_exceeded           → 예산 초과
```

## 8. 금융상품 상태

```text
likely_eligible
needs_more_info
ineligible
```

주의사항:

- `likely_eligible`도 실제 승인 상태가 아님
- `needs_more_info`는 추가 입력 또는 실제 심사가 필요
- `ineligible`은 현재 입력값 기준 명시적인 조건 불충족
- 금융상품 문구에는 실제 승인 결과가 아니라는 안내 필요

## 9. 지역 필터 연동

현재 AI 엔진은 실제 통근시간을 직접 계산하지 않습니다.

백엔드 또는 별도 교통 모듈이 통근 가능한 자치구를 계산한 뒤 다음 필드로 전달할 수 있습니다.

```json
{
  "allowed_district_names": [
    "강북구",
    "도봉구"
  ]
}
```

지역 제한을 사용하지 않으면 `null`을 전달합니다.

## 10. 필수 데이터 파일

API 실행 시 다음 파일이 필요합니다.

```text
data/processed/housing/market/monthly_rent_market_summary.csv
data/processed/housing/market/jeonse_market_summary.csv
data/processed/finance/loan_product_master.csv
data/processed/finance/loan_eligibility_rules.csv
```

파일이 없으면 추천 엔진을 초기화하거나 요청을 처리할 수 없습니다.

## 11. 에러 응답

### 422

입력값 형식 또는 허용 범위를 위반한 경우입니다.

예시:

- `top_n`이 10보다 큼
- 정의되지 않은 계약 형태
- 음수 소득 또는 음수 보유자금
- 정의되지 않은 추가 필드 전달

### 500

추천 처리 중 예상하지 못한 내부 오류가 발생한 경우입니다.

### 503

시장 데이터 또는 금융상품 데이터가 준비되지 않은 경우입니다.

## 12. 테스트

전체 테스트:

    python -m pytest -q

현재 기준:

```text
14 passed
```

API 테스트:

    python -m pytest -q \
      tests/test_housing_recommendation_api.py

추천 엔진 테스트:

    python -m pytest -q \
      tests/test_housing_plan_recommender_v1_2.py

## 13. 현재 미구현 범위

- 실시간 매물 추천
- 실제 교통시간 계산
- 공공임대 실시간 공고
- 실제 관리비 조회
- 신혼·다자녀·병역 특례
- 대환대출
- 갱신계약 특례
- 쉐어하우스 특례
- 실제 금융기관 승인 여부 확인

## 14. 변경 관리

백엔드 연동 중 다음 파일의 필드명은 임의로 변경하지 않습니다.

```text
ai_engine/api/schemas.py
ai_engine/api/service.py
ai_engine/api/app.py
examples/housing_recommendation_request.json
```

요청 또는 응답 구조를 변경할 때는 다음 순서로 진행합니다.

1. AI·백엔드 간 필드 변경 합의
2. 별도 Git 브랜치에서 수정
3. API 테스트 수정
4. 전체 테스트 통과 확인
5. Pull Request 생성
6. 백엔드 반영
