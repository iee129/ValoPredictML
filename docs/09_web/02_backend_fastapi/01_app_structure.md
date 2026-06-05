# 01. FastAPI 앱 구조

## 1. 패키지 위치

새 백엔드는 저장소 루트의 `valo_web_backend/` 패키지로 둔다. 기존 `app/`(Streamlit + `predict.py`)을 import해서 쓰므로, `valo_web_backend/`는 루트에서 `python -m valo_web_backend.main` 또는 `uvicorn valo_web_backend.main:app`으로 실행한다.

```
ValoPredictML/
├── app/                      # 기존 — Streamlit UI + predict.py (재사용 대상)
│   ├── main.py
│   └── predict.py            # ★ FastAPI가 import하는 예측 진입점
├── ml/                       # 기존 — 모델/전처리 코어
├── valo_web_backend/                      # ★ 신규 — FastAPI 백엔드
│   ├── __init__.py
│   ├── main.py               # FastAPI 앱 생성, CORS, 라우터 등록, startup 워밍업
│   ├── deps.py               # 공용 의존성 (경로, 예외→HTTP 변환)
│   ├── schemas.py            # Pydantic v2 요청/응답 모델
│   ├── serializers.py        # PredictionResult → 응답 dict 변환
│   ├── services/
│   │   └── prediction.py     # app.predict 얇은 래퍼
│   └── routers/
│       ├── predict.py        # POST /predict
│       ├── replay.py         # GET /replay/matches, GET /replay/{match_key}
│       ├── options.py        # GET /options, /agents, /maps, /players, /years
│       └── model.py          # GET /model, GET /health
└── ...
```

> `valo_web_backend/`는 `app/`·`ml/`·`docs/`와 함께 GitHub에 커밋 가능한 영역이다(`.gitignore` 허용목록에 `/valo_web_backend/`, `/valo_web_backend/**`를 추가하면 됨 — 현재는 미포함이므로 한 줄 추가 필요). 학습 산출물(`models/`, `data/`, `reports/`)은 계속 로컬 전용.

---

## 2. `valo_web_backend/main.py` 골격

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from valo_web_backend.routers import predict, replay, options, model
from valo_web_backend.services.prediction import warmup


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 콜드스타트 비용을 시연 전에 흡수: 모델 로드 + 이전연도 이력 캐시 채우기
    warmup()
    yield


app = FastAPI(title="ValoPredictML API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 배포 시 도메인 추가
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(model.router)      # /health, /model
app.include_router(options.router)    # /options, /agents, /maps, /players, /years
app.include_router(predict.router)    # /predict
app.include_router(replay.router)     # /replay/*
```

---

## 3. `valo_web_backend/services/prediction.py` — 재사용 래퍼

모델 로직은 전부 `app.predict`에 있다. 서비스 계층은 그것을 호출하고 예외를 정규화한다.

```python
from functools import lru_cache
from app.predict import (
    predict_custom_lineup, predict_replay_match,
    available_options, load_model, load_reports, global_feature_importance,
)

def warmup() -> None:
    load_model()            # ensemble.joblib + meta.json 로드 (lru_cache)
    available_options()     # maps/agents/players/years 1회 계산 (st.cache_data 미사용 경로)

@lru_cache(maxsize=1)
def options_cache() -> dict:
    return available_options()
```

> `app/predict.py`의 `load_model`·`load_reports`·`_historical_match_inputs`·`_history_state_before_year`는 이미 `lru_cache`가 걸려 있다. FastAPI 프로세스가 살아있는 동안 캐시가 유지되므로 두 번째 요청부터 빠르다. 단 `available_options()`는 캐시가 없으니 서비스 계층에서 한 번 감싼다(위 `options_cache`).

---

## 4. 예외 → HTTP 매핑 (`valo_web_backend/deps.py`)

`predict_custom_lineup`은 잘못된 입력에 `ValueError`를 던진다(메시지는 한국어). 이를 422/400으로 변환한다.

| `app.predict` 예외 | HTTP | 예시 메시지 |
|--------------------|------|-------------|
| `ValueError("선수 10명을 모두 선택해야 합니다.")` | 422 | 슬롯 누락 |
| `ValueError("10개 슬롯 안에서 같은 선수를 중복...")` | 422 | 선수 중복 |
| `ValueError("A팀 안에서 같은 요원을 중복...")` | 422 | 팀 내 요원 중복 |
| `ValueError("알 수 없는 요원입니다: ...")` | 422 | 미지의 요원 |
| `ValueError("알 수 없는 맵입니다: ...")` | 422 | 미지의 맵 |
| `ValueError("테스트 split에서 경기 키를...")` | 404 | replay match_key 없음 |
| `FileNotFoundError` (모델/데이터 부재) | 503 | 산출물 미생성 → 런북 안내 |

```python
from fastapi import HTTPException

def to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, ValueError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=503, detail="모델/데이터 산출물이 없습니다. demo_runbook 참조")
    raise exc
```

---

## 5. 관련 문서

- 모델 서빙·캐싱 상세 → [02_model_serving.md](02_model_serving.md)
- 엔드포인트 명세 → [03_endpoints.md](03_endpoints.md)
- 스키마 → [04_schemas.md](04_schemas.md)
