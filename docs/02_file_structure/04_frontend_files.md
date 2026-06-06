# 04. 프론트엔드 파일 상세 (`web/`)

마지막 업데이트: 2026-06-06

> **현행 프런트엔드는 Next.js 16(`web/`)이다.** 초기엔 Streamlit 로컬 앱(`app/main.py`)으로 시연했으나 폐기·삭제됐다. 추론 로직만 `src/inference/predict.py`로 보존돼 FastAPI 백엔드(`src/api/`)가 import한다. 상세 웹 설계는 `docs/08_web/`(SSOT) 참고.

## 1. 폴더 전체 구조

```
web/                # Next.js 16 App Router, React 19, TS, Tailwind v4
├── src/app/        # 페이지 라우트: / (커스텀 5v5), /replay, /model + api/ Route Handler
├── src/components/ # UI 컴포넌트
├── src/lib/        # api.ts(/api 베이스), serverApi.ts(FastAPI 프록시)
└── src/types/      # api.ts (백엔드 schemas.py와 짝을 이루는 TS 계약)
```

추론 로직은 `src/inference/predict.py`에 보존된다(구 `app/predict.py` — 모델 로드 + 추론).

---

## 2. 기능 (3개 화면)

**책임:**
- 맵, 선수 5명, 요원 5명 (팀당) 입력 UI
- 선공/후공 선택
- 예측 실행 → 승률 + 피처 중요도 출력
- 경기 다시보기(test split replay)
- 모델 근거(피처 중요도·자연어 설명)

**실행 방법:**

```bash
uvicorn api.main:app --reload --port 8000   # 백엔드
cd web && npm run dev                        # 프런트 (http://localhost:3000)
```

---

## 3. 화면 구조 (3개 페이지)

```
[ValoPredictML - 웹 시연]
│
├── / (커스텀 5v5 예측 홈)
│   ├── 맵 선택
│   ├── 선공/후공 선택
│   ├── 팀 A / 팀 B 선수·요원 선택 (× 5)
│   ├── [예측 실행] 버튼
│   ├── 승률 출력 (팀 A: X%, 팀 B: Y%)
│   └── 역할군 분포 시각화
│
├── /replay (경기 다시보기)
│   └── 과거 경기 데이터 기반 예측 재현
│
└── /model (모델 근거)
    ├── 피처 중요도 바 차트
    └── 자연어 승부 근거
```

---

## 4. 모델 로드 패턴

서빙 모델은 `src/inference/predict.py`가 로드하고 FastAPI(`src/api/`)가 import해 호출한다.

```python
import joblib

# src/inference/predict.py 내부 — 모듈 로드 시 1회 로드 후 캐시
model = joblib.load("models/advanced/ensemble.joblib")
```

> **주의:** 서빙은 `models/advanced/ensemble.joblib` 단일 파일(VotingClassifier soft voting) 로드. rf/xgb/lgbm 개별 파일을 따로 로드하지 않음.

---

## 5. 예측 흐름

```
사용자 입력 (맵 + 팀 A/B 요원 + 선수 스탯)
        ↓
피처 벡터 생성 (179개, FEATURE_COLS_ADVANCED 계약)
  - src/domain/valorant.py 참조
  - 역할군 카운트/diff, has_controller, is_double_duelist
  - 선수 스탯 집계, 시너지 피처
  - 요원×맵 집계값 join (사전 집계 결과물)
  - map_encoded, atk_side_advantage, is_attacker_a
        ↓
ensemble_model.predict_proba(X)
  — VotingClassifier(rf+xgb+lgbm) soft voting, 단일 호출
        ↓
승률 출력 + 피처 중요도 / SHAP 시각화
```

---

## 6. 시각화 도구

| 용도 | 도구 |
|------|------|
| 승률 게이지 | React 컴포넌트 (Tailwind) |
| 역할군 분포 | 레이더 차트 |
| 피처 중요도 | 발산형 막대 차트 (A/B) |
| 자연어 근거 | 백엔드 `serializers.py` 생성 텍스트 |

---

## 7. 관련 문서

| 문서 | 내용 |
|------|------|
| [01_directory_overview.md](01_directory_overview.md) | 전체 폴더 구조 |
| [03_ml_pipeline_files.md](03_ml_pipeline_files.md) | `src/` ML 파이프라인 실행 순서 및 의존성 |
| [05_config_and_env.md](05_config_and_env.md) | `.env` 설정, 환경변수 목록 |
| [../03_architecture/01_system_overview.md](../03_architecture/01_system_overview.md) | 시스템 아키텍처 전체 |
