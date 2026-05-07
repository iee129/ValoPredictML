> ⚠️ **범위 외**: FastAPI 미사용. 본 프로젝트는 Streamlit 로컬 도구이며 API 엔드포인트 테스트는 적용되지 않는다. 본문은 참고용으로 보존된다.

# 06. 모델 테스트 설계 (웹 환경)

## 1. 테스트 환경 개요

터미널이나 Jupyter 노트북이 아닌 **웹 브라우저**에서 모델을 테스트합니다.

```
테스트 흐름:
브라우저 (/predict 페이지)
  → 요원 선택 UI
  → FastAPI POST /predict 호출
  → 승률 + 피처 중요도 응답
  → 웹 UI에서 시각화
```

---

## 2. FastAPI 엔드포인트 전체 스펙

### 2.1 `POST /predict` — 승률 예측

**요청 (Request)**

```http
POST /predict
Content-Type: application/json

{
  "map": "Ascent",
  "team_a": ["Jett", "Sova", "Viper", "Killjoy", "Skye"],
  "team_b": ["Reyna", "Breach", "Omen", "Cypher", "Fade"]
}
```

**Pydantic 스키마**

```python
# backend/schemas/predict.py
from pydantic import BaseModel, field_validator
from typing import List

VALID_MAPS = {
    "Bind", "Haven", "Split", "Ascent", "Icebox",
    "Breeze", "Fracture", "Pearl", "Lotus", "Sunset", "Abyss"
}

class PredictRequest(BaseModel):
    map: str
    team_a: List[str]
    team_b: List[str]
    
    @field_validator("map")
    @classmethod
    def validate_map(cls, v):
        if v not in VALID_MAPS:
            raise ValueError(f"알 수 없는 맵: '{v}'. 유효한 맵: {sorted(VALID_MAPS)}")
        return v
    
    @field_validator("team_a", "team_b")
    @classmethod
    def validate_team_size(cls, v):
        if len(v) != 5:
            raise ValueError(f"팀 구성은 정확히 5명이어야 합니다. (입력: {len(v)}명)")
        return v
    
    @field_validator("team_b")
    @classmethod
    def validate_no_duplicate_agents(cls, v, info):
        team_a = info.data.get("team_a", [])
        all_agents = team_a + v
        if len(set(all_agents)) != len(all_agents):
            duplicates = [a for a in all_agents if all_agents.count(a) > 1]
            raise ValueError(f"중복 요원이 있습니다: {list(set(duplicates))}")
        return v


class RoleCounts(BaseModel):
    duelist: int
    initiator: int
    controller: int
    sentinel: int
    unknown: int = 0


class PredictResponse(BaseModel):
    win_probability: float          # 팀 A의 승리 확률 (0.0 ~ 1.0)
    lose_probability: float         # 팀 A의 패배 확률
    confidence: str                 # "high" / "medium" / "low"
    team_a_role_counts: RoleCounts
    team_b_role_counts: RoleCounts
    feature_importance: dict        # 피처명 → 중요도 (XGBoost 기준)
    map: str
    model_version: str
```

**응답 예시**

```json
{
  "win_probability": 0.673,
  "lose_probability": 0.327,
  "confidence": "medium",
  "team_a_role_counts": {
    "duelist": 1,
    "initiator": 2,
    "controller": 1,
    "sentinel": 1,
    "unknown": 0
  },
  "team_b_role_counts": {
    "duelist": 1,
    "initiator": 2,
    "controller": 1,
    "sentinel": 1,
    "unknown": 0
  },
  "feature_importance": {
    "team_a_controller": 0.142,
    "team_b_duelist": 0.138,
    "map_encoded": 0.121,
    "controller_diff": 0.115,
    "team_a_initiator": 0.098
  },
  "map": "Ascent",
  "model_version": "1.0.0"
}
```

**신뢰도(confidence) 계산 기준**

```python
def calculate_confidence(prob: float) -> str:
    """예측 확률의 극단성 기반 신뢰도 분류"""
    distance = abs(prob - 0.5)
    if distance >= 0.2:    # 70%+ or 30%- 
        return "high"
    elif distance >= 0.1:  # 60%+ or 40%-
        return "medium"
    else:                  # 50% ± 10%
        return "low"
```

---

### 2.2 `GET /agents` — 요원 목록

```http
GET /agents
```

**응답**

```json
{
  "agents": [
    {"name": "Jett", "role": "Duelist", "role_kr": "타격대"},
    {"name": "Reyna", "role": "Duelist", "role_kr": "타격대"},
    {"name": "Sova", "role": "Initiator", "role_kr": "척후대"},
    ...
  ],
  "roles": {
    "Duelist": {"name_kr": "타격대", "count": 8},
    "Initiator": {"name_kr": "척후대", "count": 7},
    "Controller": {"name_kr": "전략가", "count": 6},
    "Sentinel": {"name_kr": "감시자", "count": 6}
  }
}
```

---

### 2.3 `GET /maps` — 맵 목록

```http
GET /maps
```

**응답**

```json
{
  "maps": [
    "Ascent", "Bind", "Haven", "Split", "Icebox",
    "Breeze", "Fracture", "Pearl", "Lotus", "Sunset", "Abyss"
  ]
}
```

---

### 2.4 `GET /history` — 예측 기록

```http
GET /history?limit=20&offset=0&map=Ascent
```

**응답**

```json
{
  "total": 142,
  "items": [
    {
      "id": 142,
      "created_at": "2024-01-15T18:30:00",
      "map": "Ascent",
      "team_a_agents": ["Jett", "Sova", "Viper", "Killjoy", "Skye"],
      "team_b_agents": ["Reyna", "Breach", "Omen", "Cypher", "Fade"],
      "win_probability": 0.673,
      "confidence": "medium"
    },
    ...
  ]
}
```

---

### 2.5 `GET /health` — 서버 상태 확인

```http
GET /health
```

**응답**

```json
{
  "status": "ok",
  "model_loaded": true,
  "model_version": "1.0.0",
  "trained_at": "2024-01-10T12:00:00"
}
```

---

## 3. FastAPI 구현 코드

### 3.1 main.py

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import predict, agents, maps, history

app = FastAPI(
    title="ValoPredictML API",
    version="1.0.0",
    description="발로란트 팀 조합 승률 예측 API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(predict.router, tags=["prediction"])
app.include_router(agents.router, tags=["agents"])
app.include_router(maps.router, tags=["maps"])
app.include_router(history.router, tags=["history"])

@app.get("/health")
def health_check():
    from services.prediction_service import PredictionService
    svc = PredictionService()
    return {
        "status": "ok",
        "model_loaded": svc.is_loaded(),
        "model_version": svc.get_version(),
    }
```

### 3.2 predict 라우터

```python
# backend/routers/predict.py
from fastapi import APIRouter, HTTPException
from schemas.predict import PredictRequest, PredictResponse
from services.prediction_service import PredictionService

router = APIRouter()
service = PredictionService()

@router.post("/predict", response_model=PredictResponse)
async def predict_win_rate(request: PredictRequest):
    try:
        result = service.predict(
            map_name=request.map,
            team_a=request.team_a,
            team_b=request.team_b
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예측 오류: {str(e)}")
```

### 3.3 prediction_service.py

```python
# backend/services/prediction_service.py
import joblib
import numpy as np
from ml.feature_engineer import FeatureEngineer
from ml.agent_roles import AGENT_ROLE_MAP
import json

class PredictionService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance
    
    def __init__(self):
        if not self._loaded:
            self._load_models()
    
    def _load_models(self):
        import os
        model_path = os.environ.get("MODEL_PATH", "./models")
        self.rf_model   = joblib.load(f"{model_path}/rf_model.joblib")
        self.xgb_model  = joblib.load(f"{model_path}/xgboost_model.joblib")
        self.lgbm_model = joblib.load(f"{model_path}/lgbm_model.joblib")
        self.le_map = joblib.load(f"{model_path}/label_encoder_map.joblib")
        
        with open(f"{model_path}/model_metadata.json") as f:
            self.metadata = json.load(f)
        
        self.engineer = FeatureEngineer(self.le_map)
        self._loaded = True
        print("[INFO] 모델 로드 완료")
    
    def predict(self, map_name: str, team_a: list, team_b: list) -> dict:
        features = self.engineer.transform(map_name, team_a, team_b)
        
        rf_prob   = self.rf_model.predict_proba(features)[0, 1]
        xgb_prob  = self.xgb_model.predict_proba(features)[0, 1]
        lgbm_prob = self.lgbm_model.predict_proba(features)[0, 1]
        
        # 단순 평균 (RF + XGBoost + LightGBM, 1/3씩)
        win_prob = float((rf_prob + xgb_prob + lgbm_prob) / 3.0)
        
        # 피처 중요도 (XGBoost 기준)
        importance = dict(zip(
            self.metadata["features"],
            self.xgb_model.feature_importances_.tolist()
        ))
        top_importance = dict(sorted(importance.items(), key=lambda x: -x[1])[:5])
        
        return {
            "win_probability": round(win_prob, 4),
            "lose_probability": round(1 - win_prob, 4),
            "confidence": calculate_confidence(win_prob),
            "team_a_role_counts": get_role_counts(team_a),
            "team_b_role_counts": get_role_counts(team_b),
            "feature_importance": top_importance,
            "map": map_name,
            "model_version": self.metadata.get("model_version", "1.0.0"),
        }
    
    def is_loaded(self) -> bool:
        return self._loaded
    
    def get_version(self) -> str:
        return self.metadata.get("model_version", "unknown") if self._loaded else "not_loaded"
```

---

## 4. 테스트 시나리오

### 4.1 정상 케이스

| 시나리오 | 입력 | 기대 결과 |
|---|---|---|
| 균형 잡힌 조합 | 양 팀 모두 1타격대 + 1척후대 + 1전략가 + 2감시자 | 50% 근처 확률 |
| 전략가 없는 팀 | 팀 A에 전략가 없음 | 팀 A 승률 낮음 |
| 타격대 과다 | 팀 A에 타격대 5명 | 팀 A 승률 낮음 |
| 맵별 차이 | 같은 조합, 맵만 변경 | 맵에 따라 확률 변화 |

### 4.2 엣지 케이스

| 시나리오 | 입력 | 기대 결과 |
|---|---|---|
| 같은 요원 중복 선택 | 팀 A와 팀 B 모두 Jett | 422 에러 반환 |
| 팀 인원 초과 | 팀 A에 6명 | 422 에러 반환 |
| 잘못된 맵 이름 | `"Icebox2"` | 422 에러 반환 |
| 신규 요원 이름 | 매핑에 없는 요원 | Unknown 처리, 예측은 계속 진행 |
| 빈 팀 | `[]` | 422 에러 반환 |

### 4.3 성능 테스트

```bash
# 응답시간 측정 (k6 또는 curl)
for i in {1..10}; do
  curl -s -o /dev/null -w "%{time_total}s\n" \
    -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d '{"map":"Ascent","team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}'
done
# 목표: 모든 응답이 200ms 이내
```

---

## 5. 웹 UI 테스트 흐름

```
1. /predict 페이지 열기
2. 맵 선택 (드롭다운)
3. 팀 A 요원 선택 (클릭 × 5)
4. 팀 B 요원 선택 (클릭 × 5)
5. "예측하기" 버튼 클릭
6. 결과 확인:
   - 승률 게이지 (애니메이션)
   - 역할군 분포 차트 (양 팀 비교)
   - 피처 중요도 바 차트 (상위 5개)
   - 신뢰도 배지 (high/medium/low)
7. "기록 저장" 또는 새 예측
```

---

## 6. 로컬 개발 실행 방법

```bash
# 1. 가상환경 활성화
source .venv/bin/activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경변수 설정
cp .env.example .env
# .env 파일에서 DB, API Key 설정

# 4. FastAPI 서버 실행
cd backend
uvicorn main:app --reload --port 8000

# 5. API 문서 확인 (자동 생성)
# http://localhost:8000/docs   (Swagger UI)
# http://localhost:8000/redoc  (ReDoc)

# 6. 빠른 테스트 (curl)
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Ascent",
    "team_a": ["Jett", "Sova", "Viper", "Killjoy", "Skye"],
    "team_b": ["Reyna", "Breach", "Omen", "Cypher", "Fade"]
  }'
```

---

## 7. 에러 코드 정의

| HTTP Status | 에러 코드 | 설명 |
|---|---|---|
| 422 | `INVALID_MAP` | 유효하지 않은 맵 이름 |
| 422 | `INVALID_TEAM_SIZE` | 팀 인원이 5명이 아님 |
| 422 | `DUPLICATE_AGENT` | 중복 요원 선택 |
| 500 | `MODEL_NOT_LOADED` | 모델 파일 없음 |
| 500 | `PREDICTION_FAILED` | 예측 중 내부 오류 |
| 503 | `SERVICE_UNAVAILABLE` | 서버 초기화 중 |

---

## 8. 검증 문서 참조

이번 세션에서 추가된 ML 검증 문서:

| 문서 | 경로 | 내용 |
|------|------|------|
| ML 개념 검증 | [`ml_concept_validation.md`](./ml_concept_validation.md) | GroupKFold, 앙상블, SHAP, 증강 방법론 검증 |
| 프로젝트 차별점 | [`project_differentiation.md`](./project_differentiation.md) | 5개 차별점 + 기술 스택 점검표 |
| 검증 결과 종합 | [`verification_summary.md`](./verification_summary.md) | AUC=0.935, gap=0.004, +29.13%p 결과 종합 |
