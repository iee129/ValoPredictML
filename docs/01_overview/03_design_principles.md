# 03. 설계 원칙

마지막 업데이트: 2026-05-05

## 1. 방어적 데이터 처리 (Defensive Data Handling)

시스템이 예상치 못한 입력에도 오류 없이 동작하도록 설계합니다.

### 1.1 신규 요원 방어 처리

Valorant는 지속적으로 신규 요원을 출시합니다.
학습 데이터에 없는 요원이 입력되면 `None`을 반환하여 품질 검사에서 제외합니다.

```python
# ml/agent_roles.py
AGENT_ROLE_MAP: dict[str, str] = {
    "Jett": "Duelist",
    "Reyna": "Duelist",
    # ... 알려진 모든 요원 (29종) ...
}

def normalize_agent(raw: str) -> str | None:
    """
    처리 순서:
    1. AGENT_ROLE_MAP에 그대로 있으면 반환
    2. 소문자 → AGENT_ALIASES 조회 ("kayo" → "KAY/O")
    3. .title() 시도 후 재확인
    4. 없으면 None → 품질 검사에서 제외
    """
    if raw in AGENT_ROLE_MAP:
        return raw
    alias = AGENT_ALIASES.get(raw.lower())
    if alias:
        return alias
    titled = raw.title()
    if titled in AGENT_ROLE_MAP:
        return titled
    return None
```

- `None` 반환 시 해당 맵 행은 품질 검사에서 제외
- `reports/rejected_matches.csv`에 탈락 사유 기록

### 1.2 결측 데이터 처리

| 상황 | 처리 방법 |
|------|-----------|
| KAST 결측 (행 레벨) | 동일 경기 팀 평균으로 imputation |
| KAST 결측 (이벤트 전체) | `-1` 플래그로 채워 모델이 "KAST 없음" 패턴 학습 |
| clutch_% 결측 | 0으로 대체 (기여 없음 = 0회) |
| agent_map_wr 집계 불가 | 0.5 (중립) 대체 |
| fk_fd_ratio FD=0 | 1.0 대체 (극단값 방지) |
| agent_experience 신규 | 0으로 대체 (경험 없음 = 0회) |
| 팀당 요원 5명 미만/초과 | 품질 검사에서 제외 |
| 알 수 없는 요원 | 품질 검사에서 제외 |
| 알 수 없는 맵 | 품질 검사에서 제외 |

### 1.3 Streamlit UI 입력 검증

```python
# app/main.py (Streamlit UI)
def validate_lineup(agents_a: list[str], agents_b: list[str]) -> list[str]:
    errors = []
    if len(agents_a) != 5:
        errors.append("팀 A는 정확히 5명이어야 합니다.")
    if len(agents_b) != 5:
        errors.append("팀 B는 정확히 5명이어야 합니다.")
    for agent in agents_a + agents_b:
        if normalize_agent(agent) is None:
            errors.append(f"알 수 없는 요원: {agent}")
    return errors
```

---

## 2. 역할군 기반 피처 전략

### 2.1 개별 요원 피처화의 문제

- 27종 요원 × One-Hot = **54개 피처** → 고차원, 과적합 (당시 27종 기준 예시, 현재는 29종)
- 신규 요원 출시 시 모델 재학습 필요
- 경기 수가 적은 요원에 대한 학습 신뢰도 저하

### 2.2 역할군 카운트 피처의 이점

```
팀 A 요원 5명 → 역할군 카운트 4개 (고정)
팀 B 요원 5명 → 역할군 카운트 4개 (고정)
diff 피처 4개 + has_controller 2개 + is_double_duelist 2개
+ 선수 스탯 12개 + 시너지 6개 + 요원조합 6개 + 맵 3개
= 총 43개 피처
```

> **주의**: 이 43피처 설계는 구 명세이며, 현재 서빙 모델은 baseline 178피처 / advanced 125피처를 사용한다.

- 신규 요원도 역할군으로 자동 일반화
- 메타 변화에 강건한 구조적 피처

### 2.3 diff 피처의 의미

```python
diff_duelist    = a_duelist    - b_duelist    # 양수: 팀 A가 더 많음
diff_initiator  = a_initiator  - b_initiator
diff_controller = a_controller - b_controller
diff_sentinel   = a_sentinel   - b_sentinel
```

---

## 3. 모듈형 아키텍처 (Modular Architecture)

### 3.1 역할 분리 원칙

각 모듈은 **하나의 책임**만 가집니다.

| 모듈 | 책임 | 하지 말아야 할 것 |
|------|------|-----------------|
| `ml/agent_roles.py` | 요원→역할군 매핑, 맵 목록, 정규화 함수 | 파싱·학습 로직 포함 금지 |
| `ml/baseline/preprocess.py` | baseline 전처리 파이프라인 진입점 | 모델 학습 금지 |
| `ml/parsers/*.py` | 소스별 CSV 파싱 | 피처 생성 금지 |
| `ml/baseline/train.py` | baseline 모델 학습 (GridSearchCV) | API 서빙 금지 |
| `ml/advanced/ensemble.py` | advanced 앙상블 학습 (RF+XGB+LGBM) | API 서빙 금지 |
| `ml/advanced/optimize.py` | Optuna HPO (TPESampler 50 trials) | 학습 로직 직접 구현 금지 |
| `ml/baseline/evaluate.py` / `ml/advanced/evaluate.py` | 성능 평가 | DB 접근 금지 |
| `ml/advanced/shap_analysis.py` | SHAP TreeExplainer 기여도 산출 | DB 접근 금지 |
| `app/main.py` | UI 렌더링 + 예측 호출 | 학습 로직 직접 구현 금지 |

### 3.2 의존성 방향

```
[Streamlit UI]
     ↓ Python 함수 호출
[Feature Builder] → [models/*.joblib]
     ↓
[PostgreSQL 예측 기록 저장 (후보)]
```

- Streamlit 앱은 학습된 모델을 joblib으로 로드하여 직접 호출
- 별도 API 서버 없음

### 3.3 공유 상태 최소화

- ML 모델은 Streamlit 세션 시작 시 **1회 로드 후 캐시**
- 각 예측 요청은 독립적으로 처리 (상태 공유 없음)

```python
# app/predict.py (모델 로드)
import joblib

@st.cache_resource
def load_model():
    model = joblib.load("models/advanced/ensemble.joblib")  # 단일 VotingClassifier(soft)
    return model
```

---

## 4. 데이터 분리 원칙

### 4.1 match_key 단위 분할

한 경기(match_key)의 맵들이 train/val에 분산되면 같은 경기가 학습·평가에 같이 들어갑니다.
`GroupShuffleSplit`으로 경기 전체를 한 분할에 묶습니다.

### 4.2 피처 사전 집계 순서 (train 기준)

```
Step 1. train/val/test 분할 확정
Step 2. train.csv만으로:
          - atk_side_advantage 집계
          - agent_map_stats (요원×맵 승률·픽률)
          - agent_experience (선수×요원 등장 횟수)
Step 3. val/test에 집계값 join (신규 조합 → 중립값)
```

val/test 데이터가 집계에 포함되면 미래 정보가 섞임 — 절대 금지.

---

## 5. 보안 원칙

| 원칙 | 구현 방법 |
|------|-----------|
| 시크릿 하드코딩 금지 | 모든 키는 `.env` 파일, 코드에 직접 작성 절대 금지 |
| Kaggle 인증 | `~/.kaggle/kaggle.json` (홈 디렉토리, 리포 외부) |
| `.gitignore` 필수 항목 | `.env`, `.venv/`, `data/raw/`, `data/processed/`, `models/*.joblib` |

---

## 6. 개발 원칙 요약

1. 딥러닝(PyTorch, TensorFlow) 금지 — Tabular 데이터 기반 Tree-based ML만 사용
2. FastAPI/Next.js/클라우드 배포 금지 — Streamlit 로컬 도구만
3. API Key 및 비밀번호는 `.env` 환경변수로 관리, GitHub 커밋 절대 금지
4. `data/raw/`, `data/processed/`, `models/` 는 `.gitignore` 처리

---

## 7. 관련 문서

| 문서 | 내용 |
|------|------|
| [01_project_summary.md](01_project_summary.md) | 프로젝트 소개, 핵심 아이디어 |
| [02_tech_stack.md](02_tech_stack.md) | 기술 스택 선택 이유 |
| [../03_architecture/01_system_overview.md](../03_architecture/01_system_overview.md) | 시스템 아키텍처 다이어그램 |
