# 04. API 설계

마지막 업데이트: 2026-05-04

> **현행 API는 FastAPI(`src/api`)다.** 실제 HTTP 계약(엔드포인트·요청/응답 스키마)의 SSOT는 `docs/08_web/02_backend_fastapi/`다. 라우터: `predict`/`replay`/`options`/`model`/`insights`. 실행: `uvicorn api.main:app`.
>
> 아래 내용은 FastAPI 라우터가 호출하는 **`src/inference/predict.py`의 내부 Python 함수 인터페이스** 설계안이다.

---

## 1. 추론 모듈 내부 함수 인터페이스

FastAPI 라우터가 `src/inference/predict.py`의 Python 함수를 호출합니다.

### 1.1 예측 함수 (설계안)

> **실제 구현 함수명**: `predict_custom_lineup()` / `predict_replay_match()` (`src/inference/predict.py` 참조). 아래 시그니처는 내부 설계안이며 실제 파일의 함수명과 다를 수 있다.

```python
def predict_custom_lineup(
    map_name: str,
    players_a: list[dict],   # [{player, agent, acs, kd, kast, adr, fk, fd}] × 5
    players_b: list[dict],
    is_attacker_a: int,      # 1 = 팀 A 선공, 0 = 팀 B 선공
) -> dict:
    """
    반환:
    {
        "team_a_win_probability": 0.617,
        "team_b_win_probability": 0.383,
        "team_a_roles": {"duelist": 1, "initiator": 2, "controller": 1, "sentinel": 1},
        "team_b_roles": {"duelist": 1, "initiator": 1, "controller": 2, "sentinel": 1},
        "feature_importance": [{"feature": "diff_controller", "value": 0.21}, ...],
    }
    """
```

### 1.2 교체 시뮬레이션 함수 (설계안)

> **실제 구현**: `src/inference/predict.py` 내 교체 시뮬레이션 로직 참조. 아래 시그니처는 설계안이다.

```python
def simulate_swap(
    base_result: dict,
    swap_type: str,    # "agent" 또는 "player"
    team: str,         # "a" 또는 "b"
    slot: int,         # 0~4
    new_value: str,    # 새 요원 이름 또는 선수 이름
) -> dict:
    """
    반환:
    {
        "new_win_probability": 0.643,
        "delta": +0.026,   # 교체 전후 승률 변화량
    }
    """
```

### 1.3 최적 요원 조합 탐색 함수 (설계안)

> **실제 구현**: `src/inference/predict.py` 참조. 아래 시그니처는 설계안이다.

```python
def find_best_agents(
    map_name: str,
    player_stats: list[dict],
    top_n: int = 5,
) -> list[dict]:
    """
    29종에서 5종 선택 = C(29,5) = 118,755가지 순차 스코어링
    반환: [{"agents": [...], "win_probability": 0.71}, ...] × top_n
    """
```

---

## 2. 입력 검증 (백엔드 Pydantic + 프런트 폼)

| 조건 | 처리 |
|------|------|
| 팀당 요원 정확히 5명 | 미충족 시 예측 버튼 비활성화 + 경고 |
| 유효한 요원 이름 | `normalize_agent()` → None 이면 경고 |
| 유효한 맵 이름 | `normalize_map()` → None 이면 경고 |
| 선수 스탯 결측 | 허용 (결측 피처는 중립값 대체) |

---

## 3. 출력 형태

### 3.1 승률 예측 결과

| 항목 | 설명 |
|------|------|
| `team_a_win_probability` | 팀 A 승률 0.0~1.0 |
| `team_b_win_probability` | `1 - team_a_win_probability` |
| `team_a_roles` | 팀 A 역할군 카운트 dict |
| `team_b_roles` | 팀 B 역할군 카운트 dict |
| `feature_importance` | 상위 피처 중요도 리스트 |

### 3.2 앙상블 계산

```
단일 ensemble.joblib (VotingClassifier soft voting, weights=[2.0, 3.0, 0.1]) 로드
    → ensemble_model.predict_proba(X) 1회 호출
    → 내부적으로 RF + XGBoost + LightGBM 가중평균 처리
    → 최종 팀 A 승률 반환

# 개별 rf/xgb/lgbm 모델을 따로 로드하거나 직접 평균하지 않음
# 서빙 경로: src/inference/predict.py → models/advanced/ensemble.joblib
```

---

## 4. 관련 문서

| 문서 | 내용 |
|------|------|
| [02_request_flow.md](02_request_flow.md) | 예측 요청 처리 흐름 |
| [../02_file_structure/04_frontend_files.md](../02_file_structure/04_frontend_files.md) | `web/` Next.js 프런트엔드 구조 |
| [../08_web/02_backend_fastapi/](../08_web/02_backend_fastapi/) | FastAPI HTTP API 계약 (SSOT) |
| [06_ml_pipeline_architecture.md](06_ml_pipeline_architecture.md) | ML 파이프라인 상세 |
