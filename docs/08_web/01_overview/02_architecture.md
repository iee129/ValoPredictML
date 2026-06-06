# 02. 아키텍처

## 1. 3계층 구성

```
┌──────────────────────────────────────────────────────────────────────┐
│  계층 1 — Next.js 16 프론트엔드 (TypeScript)            :3000          │
│                                                                        │
│  app/page.tsx (홈)  app/replay/  app/model/  app/history/              │
│        │                      │                      │                 │
│        └──────────────┬───────┴──────────────────────┘                 │
│                       ▼                                                │
│  lib/api.ts  ── 타입 안전 fetch 래퍼 (types/api.ts) ──┐                │
│  app/api/**/route.ts ── proxyGet/proxyPost → FastAPI                   │
└───────────────────────────────────────────────────────┼───────────────┘
                                                         │ HTTP/JSON
                                                         │ VALO_INTERNAL_API_URL
                                                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  계층 2 — FastAPI 백엔드 (api/)                         :8000          │
│                                                                        │
│  routers/predict.py  routers/options.py  routers/model.py              │
│  routers/history.py  (/history, /history/{id})                         │
│        │                      │                    │                   │
│        ▼                      ▼                    ▼                   │
│  services/prediction.py  ── inference.predict 래핑                     │
│  services/history.py     ── SQLAlchemy Core (prediction_history)       │
│        │  predict_custom_lineup / predict_replay_match /           │   │
│        │  available_options / load_model / load_reports            │   │
└────────┼───────────────────────────────────────────────────────────┼───┘
         │ import (재사용, 재구현 X)                    │ (선택적, graceful)
         ▼                                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│  계층 3-A — 학습 산출물 + ML 코어 (로컬 파일, .gitignore)              │
│                                                                        │
│  src/inference/predict.py ─ src/features/preprocess.py                 │
│  models/advanced/ensemble.joblib (179F)                                │
│  data/processed/{matches,players}.csv, advanced/test.csv               │
│  reports/advanced/{metrics,validation}.json                            │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  계층 3-B — PostgreSQL (선택, VALO_DATABASE_URL 설정 시 활성)           │
│                                                                        │
│  docker-compose.yml: postgres:18-alpine, 호스트 포트 5433              │
│  테이블: prediction_history (id, created_at, map, cutoff_year,         │
│           predicted_winner, confidence, team_*_name/probability,       │
│           request_json JSONB, response_json JSONB)                     │
│                                                                        │
│  미설정 시 /history → 503, /predict·/replay 등은 영향 없음             │
└──────────────────────────────────────────────────────────────────────┘
```

**핵심 설계 원칙: 백엔드는 모델 로직을 재구현하지 않는다.** 계층 2는 계층 3의 `src/inference/predict.py`를 import해 호출하고 결과를 직렬화만 한다. 피처 생성·정규화·이전연도 조회·앙상블 추론은 전부 기존 코드 경로를 탄다. 이로써 추론 로직(`src/inference/predict.py`)과 웹 API가 **동일한 예측 결과**를 보장한다.

---

## 2. 커스텀 예측 요청 흐름 (`POST /predict`)

```
[프론트] /predict 페이지
  사용자: 맵 + 기준연도 + 팀A 5×{선수,요원} + 팀B 5×{선수,요원}
    │
    ▼ lib/api.ts → fetch POST /predict  (PredictRequest)
[백엔드] routers/predict.py
    │ Pydantic 검증 (5쌍×2, 맵 화이트리스트, 연도 범위)
    ▼ services/prediction.py
    │ inference.predict.predict_custom_lineup(map, cutoff_year, team_a_slots, team_b_slots)
    │     ├─ _history_state_before_year(...)   # 기준연도 이전 선수/맵·요원/선수·요원 이력 (lru_cache)
    │     ├─ _build_feature_row(...)           # 179피처 1행 생성 (include_diff=False)
    │     └─ ensemble.predict_proba(X)[:,1]    # 팀 A 승률
    ▼ PredictionResult → serialize_prediction()  → PredictResponse(JSON)
[프론트] setState(result) → 게이지/레이더/피처바 렌더
```

> **콜드스타트 주의**: 첫 `/predict`는 `data/processed`에서 이전연도 이력 상태를 구축하느라 수 초~수십 초 걸릴 수 있다(`_historical_match_inputs`, `_history_state_before_year`가 `lru_cache`). 두 번째 호출부터 빠르다. 자세히 → [../02_backend_fastapi/02_model_serving.md](../02_backend_fastapi/02_model_serving.md).

---

## 3. 경기 다시보기 흐름 (`/replay`)

```
[프론트] /replay 페이지
    │ GET /replay/matches?limit=200  → [{match_key, label, date, map, team_a, team_b}]
    │ 사용자가 경기 1건 선택
    ▼ GET /replay/{match_key}
[백엔드] inference.predict.predict_replay_match(match_key)
    │ test.csv에서 해당 행 로드 → build_xy(advanced) → 추론
    ▼ PredictResponse + {actual_label, match_key} 포함
[프론트] 예측 승자 vs 실제 승자 대조 표시
```

replay는 피처가 `test.csv`에 이미 계산돼 있어 **콜드스타트가 없고** 시연 시 가장 안정적이다.

---

## 4. 기동 시 데이터 흐름 (`/options`)

프론트는 페이지 진입 시 `GET /options`로 입력 위젯 데이터를 한 번에 받는다. 이는 `available_options()`를 그대로 직렬화한다:

| 키 | 출처 (`src/inference/predict.py`) | 용도 |
|----|--------------------------|------|
| `maps` | `matches.csv`에 등장하는 `MAP_ORDER` 맵 | 맵 드롭다운 |
| `agents` | `sorted(AGENT_ROLE_MAP)` (29종) | 요원 셀렉트 |
| `players` | kaggle 소스 선수 빈도순 | 선수 자동완성 |
| `years` | 등장 연도 + (max+1) | 기준연도 드롭다운 |

`replay_matches`는 양이 많아 `/options`에서 분리해 `/replay/matches`로 별도 제공한다.

---

## 5. 관련 문서

- 백엔드 앱 구조 → [../02_backend_fastapi/01_app_structure.md](../02_backend_fastapi/01_app_structure.md)
- 모델 서빙/캐싱 → [../02_backend_fastapi/02_model_serving.md](../02_backend_fastapi/02_model_serving.md)
- 프론트 데이터 흐름 → [../03_frontend_nextjs/03_predict_page.md](../03_frontend_nextjs/03_predict_page.md)
