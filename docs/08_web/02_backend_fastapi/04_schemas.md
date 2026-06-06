# 04. Pydantic 스키마 ↔ PredictionResult 매핑

Pydantic v2(FastAPI 내장) 기준. 이 스키마가 프론트 `types/api.ts`와 1:1 대응한다.

---

## 1. 요청 스키마 (`src/api/schemas.py`)

```python
from pydantic import BaseModel, Field, conlist

class Slot(BaseModel):
    player: str = Field(min_length=1)   # 선수 식별자 (필수 — 모델 이전연도 조회 키)
    agent: str = Field(min_length=1)    # 요원명 (29종 화이트리스트)

class PredictRequest(BaseModel):
    map: str
    cutoff_year: int = Field(ge=2000, le=2099)
    team_a: conlist(Slot, min_length=5, max_length=5)
    team_b: conlist(Slot, min_length=5, max_length=5)
```

> 슬롯 개수(5×2)는 Pydantic이 막고, **선수 유일성·팀내 요원 유일·맵/요원 화이트리스트**는 `predict_custom_lineup` 내부 `_validate_slots`/정규화가 `ValueError`로 막는다. 라우터에서 그 `ValueError`를 422로 변환한다([01_app_structure.md](01_app_structure.md) §4). 백엔드가 미리 한 번 더 검증해 친절한 메시지를 줘도 좋다.

라우터는 Pydantic 모델을 `inference.predict`가 기대하는 `list[dict[str,str]]`로 변환:

```python
team_a_slots = [s.model_dump() for s in req.team_a]   # [{"player":..,"agent":..}, ...]
```

---

## 2. 응답 스키마 + PredictionResult 매핑

```python
class TeamProb(BaseModel):
    name: str
    win_probability: float

class FeatureContribution(BaseModel):
    feature: str          # 실제 컬럼명 (FEATURE_COLS_ADVANCED)
    label: str            # feature_label(feature) — 한국어 (백엔드가 추가)
    value: float
    importance: float
    contribution: float

class RoleCounts(BaseModel):
    duelist: float; initiator: float; controller: float; sentinel: float

class Explanation(BaseModel):              # 자연어 근거 (C) — 06_insights/04
    feature: str; text: str; magnitude: float

class BalanceWarning(BaseModel):           # 구성 결함 (G) — 06_insights/03
    code: str
    severity: Literal["high", "medium", "low"]
    message: str

class PredictResponse(BaseModel):
    map: str | None
    cutoff_year: int | None = None
    predicted_winner: str        # "A" | "B"
    predicted_label: int
    confidence: float
    team_a: TeamProb
    team_b: TeamProb
    role_counts: dict[str, RoleCounts]      # {"team_a":..,"team_b":..}
    top_features: list[FeatureContribution]
    model: dict                              # {"contract":"advanced","n_features":179}
    # 인사이트 (06_insights) — 커스텀 예측에 함께 실어 한 화면에 표시
    explanations: list[Explanation] = []                       # 자연어 근거 (C)
    balance: dict[str, list[BalanceWarning]] = {}              # {"team_a":[...],"team_b":[...]} (G)
    # replay 전용 (커스텀에선 생략/None)
    match_key: str | None = None
    actual_label: int | None = None
    actual_winner: str | None = None
    hit: bool | None = None
    # 히스토리 DB 저장 결과 (DB 미설정 시 None)
    history_id: str | None = None
    created_at: str | None = None           # ISO 8601
```

> `explanations`/`balance`는 모델 출력이 아니라 백엔드가 파생해 덧붙인다(자연어 생성 → [../06_insights/04_nl_explanation.md](../06_insights/04_nl_explanation.md), 룰 → [../06_insights/03_balance_warning.md](../06_insights/03_balance_warning.md)). `Literal` 사용 시 `from typing import Literal` 임포트 필요.

### 매핑 표 (`PredictionResult` → `PredictResponse`)

| 응답 필드 | 출처 (PredictionResult) | 변환 |
|-----------|--------------------------|------|
| `team_a.win_probability` | `team_a_win_probability` | 그대로 |
| `team_b.win_probability` | `team_b_win_probability` | 그대로 |
| `team_a.name` / `team_b.name` | `team_a` / `team_b` | 그대로 (커스텀="A팀/B팀", replay=실제 팀명) |
| `confidence` | `confidence` | 그대로 |
| `predicted_label` | `predicted_label` | 그대로 |
| `predicted_winner` | `predicted_label` | `1→"A"`, `0→"B"` |
| `role_counts.team_a` | `role_counts["A팀"]` | 한국어 키 → canonical 키 역매핑 |
| `role_counts.team_b` | `role_counts["B팀"]` | 동일 |
| `top_features[]` | `top_features[]` | `label = feature_label(feature)` 추가 |
| `model.n_features":179) |
| `match_key`,`actual_label` | 동명 필드 | replay만 |
| `actual_winner` | `actual_label` | `1→"A"`,`0→"B"` |
| `hit` | `predicted_label==actual_label` | replay만 |

---

## 3. 직렬화 헬퍼 (`src/api/serializers.py`)

```python
from inference.predict import feature_label, role_label  # 기존 라벨 매핑 재사용

ROLE_KO_TO_KEY = {"타격대":"duelist","척후대":"initiator","전략가":"controller","감시자":"sentinel"}

def _role_counts(side: dict) -> dict:
    return {ROLE_KO_TO_KEY.get(k, k): v for k, v in side.items()}

def serialize_prediction(r) -> dict:
    return {
        "map": r.map_name,
        "predicted_winner": "A" if r.predicted_label == 1 else "B",
        "predicted_label": r.predicted_label,
        "confidence": r.confidence,
        "team_a": {"name": r.team_a, "win_probability": r.team_a_win_probability},
        "team_b": {"name": r.team_b, "win_probability": r.team_b_win_probability},
        "role_counts": {
            "team_a": _role_counts(r.role_counts.get("A팀", {})),
            "team_b": _role_counts(r.role_counts.get("B팀", {})),
        },
        "top_features": [
            {**f, "label": feature_label(f["feature"])} for f in r.top_features
        ],
        "model": {
            "contract": r.model_metadata.get("feature_contract", "advanced"),
            "n_features":179),
        },
        # replay 필드
        "match_key": r.match_key,
        "actual_label": r.actual_label,
        "actual_winner": (None if r.actual_label is None
                          else ("A" if r.actual_label == 1 else "B")),
        "hit": (None if r.actual_label is None
                else r.predicted_label == r.actual_label),
    }
```

> `role_counts` 키 역매핑은 `src/inference/predict.py`의 `ROLE_LABELS`(영문→한국어)를 뒤집은 것이다. `ROLE_LABELS`가 바뀌면 `ROLE_KO_TO_KEY`도 함께 갱신해야 하므로, 가능하면 `inference.predict`에서 canonical 역할 키를 직접 받도록 추후 리팩터링을 권장(현재는 `_role_counts_from_features`가 한국어 라벨로 키를 만든다).

---

## 4. `feature_values` (선택)

`PredictionResult.feature_values`(179피처 전체값)는 심화 디버깅/풀 피처 테이블 표시에 유용하지만 응답이 커진다. 기본 응답에서 제외하고, `?include_features=true` 쿼리일 때만 포함하는 것을 권장.

---

---

## 5. 히스토리 스키마 (`src/api/schemas.py`)

```python
class HistoryItem(BaseModel):
    id: str
    created_at: str                # ISO 8601 (datetime → isoformat())
    map: str
    cutoff_year: int
    predicted_winner: str          # "A" | "B"
    confidence: float
    team_a_name: str
    team_b_name: str
    team_a_win_probability: float
    team_b_win_probability: float
    team_a_players: list[str]      # 팀 A 선수 식별자 5명
    team_b_players: list[str]      # 팀 B 선수 식별자 5명
    team_a_agents: list[str]       # 팀 A 요원명 5개
    team_b_agents: list[str]       # 팀 B 요원명 5개

class HistoryListResponse(BaseModel):
    items: list[HistoryItem]
    total: int
    limit: int
    offset: int

class HistoryDetailResponse(BaseModel):
    item: HistoryItem              # 목록 항목 (14개 필드)
    request: PredictRequest        # 원본 예측 요청 (역직렬화됨)
    result: PredictResponse        # 원본 예측 응답 (역직렬화됨)
```

`HistoryDetailResponse`는 `HistoryItem`을 상속하지 않고 `item`·`request`·`result` 세 필드를 포함한다. `request`·`result`는 `prediction_history` 테이블의 `request_json`·`response_json`(JSONB)을 Pydantic 모델로 역직렬화한 값이다.

---

## 6. 관련 문서

- 엔드포인트 → [03_endpoints.md](03_endpoints.md)
- 히스토리·DB 상세 → [06_history_and_db.md](06_history_and_db.md)
- 프론트 타입(이 스키마의 TS 거울) → [../03_frontend_nextjs/02_types_and_api_client.md](../03_frontend_nextjs/02_types_and_api_client.md)
- 계약 SSOT → [../04_integration/01_data_contract.md](../04_integration/01_data_contract.md)
