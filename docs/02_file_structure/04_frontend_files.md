# 04. 프론트엔드 파일 상세 (`app/`)

마지막 업데이트: 2026-05-22

> **범위 외 (out of scope)**: Next.js, React, Vercel 배포는 이 프로젝트에서 사용하지 않습니다. 본 프로젝트는 **Streamlit 로컬 도구**입니다.

## 1. 폴더 전체 구조

```
app/
├── __init__.py
├── main.py        # Streamlit 진입점 (미구현)
└── predict.py     # 모델 로드 + 추론 (미구현)
```

---

## 2. `app/main.py` — Streamlit 진입점

**책임:**
- 맵, 선수 5명, 요원 5명 (팀당) 입력 UI
- 선공/후공 선택
- 선수 스탯 선택 입력 (ACS, KD, KAST, ADR, 클러치율)
- 예측 실행 → 승률 + 피처 중요도 출력
- 교체 시뮬레이션 (선수/요원 교체 전후 확률 변화량)
- 맵별 최적 요원 조합 탐색 (후보)
- PostgreSQL 예측 기록 저장/조회 (후보)

**실행 방법:**

```bash
streamlit run app/main.py
```

---

## 3. 예상 UI 구조

```
[ValoPredictML - Streamlit 로컬 분석 도구]
│
├── 사이드바
│   ├── 맵 선택 (selectbox)
│   ├── 선공/후공 선택
│   └── 팀 A / 팀 B 요원 선택 (multiselect or selectbox × 5)
│
├── 메인 영역
│   ├── [예측 실행] 버튼
│   ├── 승률 출력 (팀 A: X%, 팀 B: Y%)
│   ├── 피처 중요도 바 차트 (Plotly)
│   ├── 역할군 분포 레이더 차트 (Plotly)
│   └── 교체 시뮬레이션 결과 테이블
│
└── (후보) 예측 기록 탭
    └── PostgreSQL predictions 테이블 조회
```

---

## 4. 모델 로드 패턴

```python
import streamlit as st
import joblib

@st.cache_resource
def load_models():
    """Streamlit 세션 시작 시 1회 로드 후 캐시"""
    rf  = joblib.load("models/advanced/rf.joblib")
    xgb = joblib.load("models/advanced/xgb.joblib")
    lgb = joblib.load("models/advanced/lgbm.joblib")
    return rf, xgb, lgb

rf_model, xgb_model, lgb_model = load_models()
```

---

## 5. 예측 흐름

```
사용자 입력 (맵 + 팀 A/B 요원 + 선수 스탯)
        ↓
피처 벡터 생성 (43개)
  - ml/valorant.py 참조
  - 역할군 카운트/diff, has_controller, is_double_duelist
  - 선수 스탯 집계, 시너지 피처
  - 요원×맵 집계값 join (사전 집계 결과물)
  - map_encoded, atk_side_advantage, is_attacker_a
        ↓
RF / XGBoost / LightGBM predict_proba()
        ↓
앙상블: 세 모델 예측 확률 평균
        ↓
승률 출력 + 피처 중요도 / SHAP 시각화
```

---

## 6. 시각화 도구

| 용도 | 도구 |
|------|------|
| 승률 게이지 | Streamlit metric 또는 Plotly gauge |
| 역할군 분포 | Plotly radar chart |
| 피처 중요도 | Plotly bar chart |
| 교체 delta | Streamlit dataframe |
| 예측 기록 | Streamlit dataframe (PostgreSQL 조회, 후보) |

---

## 7. 관련 문서

| 문서 | 내용 |
|------|------|
| [01_directory_overview.md](01_directory_overview.md) | 전체 폴더 구조 |
| [03_ml_pipeline_files.md](03_ml_pipeline_files.md) | `ml/` 폴더 실행 순서 및 의존성 |
| [05_config_and_env.md](05_config_and_env.md) | `.env` 설정, 환경변수 목록 |
| [../03_architecture/01_system_overview.md](../03_architecture/01_system_overview.md) | 시스템 아키텍처 전체 |
