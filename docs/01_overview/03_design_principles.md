# 03. 설계 원칙

## 1. 방어적 데이터 처리 (Defensive Data Handling)

시스템이 예상치 못한 입력에도 오류 없이 동작하도록 설계합니다.

### 1.1 신규 요원 방어 처리

Valorant는 지속적으로 신규 요원을 출시합니다.  
학습 데이터에 없는 요원이 입력되면 `Unknown`으로 처리하여 모델 오류를 방지합니다.

```python
# backend/ml/agent_roles.py
AGENT_ROLE_MAP = {
    "Jett": "Duelist",
    "Reyna": "Duelist",
    # ... 알려진 모든 요원 ...
}

def get_role(agent_name: str) -> str:
    """학습 데이터에 없는 요원 → Unknown 처리 (역할군 카운트에 미포함)"""
    return AGENT_ROLE_MAP.get(agent_name, "Unknown")
```

- `Unknown`은 역할군 카운트에 포함하지 않음 (0으로 처리)
- 경고 로그 기록 (`[WARN] Unknown agent: NewAgent2025`)
- 모델 재학습 없이 새 요원 대응 가능

### 1.2 결측 데이터 처리

| 상황 | 처리 방법 |
|---|---|
| 컬럼 값 누락 | 역할군 카운트를 0으로 대체 |
| 맵 이름 미등록 | Label Encoding fallback (Unknown 클래스로 인코딩) |
| 팀 구성 5명 미만 | 400 Bad Request 반환 |
| 팀 구성 5명 초과 | 400 Bad Request 반환 |
| 중복 요원 | 422 Validation Error 반환 |
| 동일 팀에 중복 | 422 Validation Error 반환 |

### 1.3 API 입력 검증 (Pydantic)

```python
from pydantic import BaseModel, validator, Field
from typing import List

class PredictRequest(BaseModel):
    map: str = Field(..., min_length=1, max_length=50)
    team_a: List[str] = Field(..., min_items=5, max_items=5)
    team_b: List[str] = Field(..., min_items=5, max_items=5)

    @validator('team_a', 'team_b')
    def no_duplicates(cls, v):
        if len(v) != len(set(v)):
            raise ValueError('팀 내 중복 요원 불가')
        return v

    @validator('team_b')
    def no_cross_team_duplicates(cls, team_b, values):
        team_a = values.get('team_a', [])
        overlap = set(team_a) & set(team_b)
        if overlap:
            raise ValueError(f'양 팀 중복 요원: {overlap}')
        return team_b
```

---

## 2. 역할군 기반 피처 전략

### 2.1 개별 요원 피처화의 문제

- 48종 요원 × One-Hot = **96개 피처** → 고차원, 과적합
- 신규 요원 출시 시 모델 재학습 필요
- 경기 수가 적은 요원에 대한 학습 신뢰도 저하

### 2.2 역할군 카운트 피처의 이점

```
팀 A 요원 5명 → 역할군 카운트 4개 (고정)
팀 B 요원 5명 → 역할군 카운트 4개 (고정)
Diff 피처 4개 + has_controller 2개 + 맵 인코딩 1개
= 총 15개 피처 (고정)
```

- 신규 요원도 역할군으로 자동 일반화
- 15개 피처로 80%+ 정확도 목표 달성 가능
- 피처 중요도 해석이 쉬움 ("전략가 차이가 가장 중요")

### 2.3 diff 피처의 의미

```python
duelist_diff = team_a_duelist - team_b_duelist
initiator_diff = team_a_initiator - team_b_initiator
controller_diff = team_a_controller - team_b_controller
sentinel_diff = team_a_sentinel - team_b_sentinel
```

- 양수: 팀 A가 해당 역할군 더 많음
- 음수: 팀 B가 해당 역할군 더 많음
- 0: 동일

---

## 3. 모듈형 아키텍처 (Modular Architecture)

### 3.1 역할 분리 원칙

각 모듈은 **하나의 책임**만 가집니다.

| 모듈 | 책임 | 하지 말아야 할 것 |
|---|---|---|
| `ml/data_pipeline.py` | 데이터 로드 및 전처리 | 모델 학습 금지 |
| `ml/feature_engineering.py` | 피처 변환 | DB 접근 금지 |
| `ml/train.py` | 모델 학습 | API 서빙 금지 |
| `backend/routers/*.py` | HTTP 요청 처리 | 비즈니스 로직 직접 구현 금지 |
| `backend/services/*.py` | 비즈니스 로직 | DB 직접 접근 금지 |
| `backend/database.py` | DB 세션 관리 | 비즈니스 로직 금지 |

### 3.2 의존성 방향

```
[외부 요청]
     ↓
[Router] → [Service] → [ML Predictor]
                    ↘ → [Database]
```

- Router는 Service만 호출 (직접 DB/ML 호출 금지)
- Service는 ML Predictor와 Database를 조합
- Database 모듈은 순수 CRUD만 담당

### 3.3 공유 상태 최소화

- ML 모델은 FastAPI 시작 시 **싱글톤으로 1회 로드**
- 각 요청은 독립적으로 처리 (상태 공유 없음)
- PostgreSQL 연결은 SQLAlchemy 세션 풀로 관리

```python
# backend/services/prediction_service.py
class PredictionService:
    _instance = None
    _model_loaded = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._load_models()
        return cls._instance
```

---

## 4. 확장성 고려사항

### 4.1 요원 추가 대응

신규 요원 출시 시 코드 변경 최소화:

```python
# ml/agent_roles.py에 1줄 추가만으로 대응
AGENT_ROLE_MAP["NewAgent2025"] = "Duelist"
```

모델 재학습 없이 즉시 적용 가능.

### 4.2 다중 데이터 소스

데이터 소스가 늘어도 파이프라인 구조 변경 없음:

```python
def load_all_sources() -> pd.DataFrame:
    dfs = []
    dfs.append(load_kaggle_vct())      # Kaggle VCT 2021-2023
    dfs.append(load_henrikdev())       # HenrikDev API
    # dfs.append(load_new_source())   # 새 소스 추가 시 이 줄만 추가
    return pd.concat(dfs, ignore_index=True)
```

### 4.3 모델 교체 용이성

새 모델 추가 시 `predictor.py`의 앙상블 구성만 수정:

```python
# 현재: XGBoost 60% + LightGBM 40%
# 확장: + CatBoost 20% (가중치 재조정)
ENSEMBLE_WEIGHTS = {
    "xgboost": 0.5,
    "lightgbm": 0.3,
    # "catboost": 0.2,  # 추가 시 주석 해제
}
```

---

## 5. 보안 원칙

| 원칙 | 구현 방법 |
|---|---|
| 시크릿 하드코딩 금지 | 모든 키는 `.env` 파일, 코드에 직접 작성 절대 금지 |
| SQL Injection 방지 | SQLAlchemy ORM 사용 (raw query 금지) |
| 입력값 검증 | Pydantic 스키마로 모든 API 입력 검증 |
| CORS 화이트리스트 | 허용 origin 명시적 지정 (와일드카드 `*` 사용 금지) |
| API Key 보호 | HENRIK_API_KEY는 백엔드에서만 사용 (프론트에 노출 금지) |
| `.gitignore` 필수 항목 | `.env`, `.env.local`, `riot.txt`, `*.joblib`, `data/raw/` |

---

## 6. 관련 문서

| 문서 | 내용 |
|---|---|
| [01_project_summary.md](01_project_summary.md) | 프로젝트 소개, 핵심 아이디어 |
| [02_tech_stack.md](02_tech_stack.md) | 기술 스택 선택 이유 |
| [../03_architecture/01_system_overview.md](../03_architecture/01_system_overview.md) | 시스템 아키텍처 다이어그램 |
| [../04_data_processing/04_data_cleaning.md](../04_data_processing/04_data_cleaning.md) | 방어적 데이터 처리 구현 |
