# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 한 줄 요약

ValoPredictML은 Valorant 5v5 라인업(맵 + 양 팀 선수 5명·요원 5명)을 입력받아 승리 확률과 예측 근거를 보여준다. tree-based ML만 사용(딥러닝 금지). 두 개의 프런트가 같은 모델을 서빙한다: **① `app/`의 로컬 Streamlit 앱**, **② `valo_web_frontend/`(Next.js 16 TS) + `valo_web_backend/`(FastAPI) 웹 시연**.

## 문서 지형 (헷갈리기 쉬움 — 먼저 읽을 것)

- `docs/` — 게임 도메인 리서치 + **레거시 설계안**. 실제 경로는 `docs/01_overview/...` 형태(README가 가리키는 `docs/overview.md`·`docs/datasets.md`는 없음).
- `docs/09_web` — **폐기된** 구 웹 설계. 모든 파일 상단에 "범위 외(Streamlit 대체)" 배너. `/predict`에 선수 없이 요원만 보내는 등 실제 모델 계약과 안 맞음. **참고만, 따르지 말 것.**
- `docs_web/` — **현행 웹 설계(SSOT)**. `valo_web_backend`/`valo_web_frontend` 구현의 근거. 8개 폴더(개요·백엔드·프런트·통합·부록·인사이트·스타일·테스트). 웹 작업 전 여기부터 볼 것.

요약: ML 모델/피처 진실은 `ml/`·`app/predict.py` 코드, 웹 계약 진실은 `docs_web/` + 아래 타입/스키마 파일.

## 자주 쓰는 명령어

```bash
# 환경 (Python 3.14) — .venv 사용
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # ML + FastAPI/uvicorn/pydantic/pytest 포함

# 데이터 다운로드 — Kaggle 5개 데이터셋 → data/raw/kaggle/ (~/.kaggle/kaggle.json 필요)
python dataload.py

# === Baseline 모델 (178피처, LR+DT soft voting) ===
python -m ml.baseline.preprocess          # data/processed/{matches,players}.csv → train/val/test.csv
python -m ml.baseline.train               # → models/baseline/{model,meta}.json
python -m ml.baseline.evaluate            # → reports/baseline/metrics.json
python -m ml.baseline.validate            # 누수 게이트 → reports/baseline/validation.json

# === Advanced 모델 (125피처, RF+XGB+LGBM soft voting) — 모든 프런트가 서빙하는 모델 ===
python -m ml.baseline.preprocess --feature-contract advanced     # → data/processed/adv_kaggle_only/
python -m ml.advanced.ensemble  --input data/processed/adv_kaggle_only --output models/advanced --reports reports/adv_kaggle_only
python -m ml.advanced.evaluate  --input data/processed/adv_kaggle_only --models models/advanced --reports reports/adv_kaggle_only
python -m ml.advanced.validate  --reports reports/adv_kaggle_only --models models/advanced   # AUC≥0.70 게이트, 실패 시 exit 1

# 인사이트 사전 집계 (요원-맵 적합도·메타 조합) → reports/insights/*.json
python -m ml.insights.build_insights --input data/processed --output reports/insights

# Streamlit 앱
python -m streamlit run app/main.py

# === 웹 스택 ===
# 프런트 단독(권장): 프런트 내부 mock(/api)로 데이터까지 전부 뜸 — 백엔드/데이터 불필요
cd valo_web_frontend && npm run dev        # http://localhost:3000
npx tsc --noEmit                           # 계약/타입 검증 (프런트 디렉터리에서)
npm run build && npm run lint

# 실제 백엔드(모델·데이터 산출물 필요): valo_web_frontend/.env.local 의 NEXT_PUBLIC_API_URL=http://localhost:8000 로 전환 후
uvicorn valo_web_backend.main:app --reload --port 8000
```

테스트: 백엔드는 `pytest`(requirements에 포함, 테스트는 커밋 안 됨 — `docs_web/08_testing` 참조), 프런트는 `tsc --noEmit` + `eslint`. `tests/`·`scripts/`는 `.gitignore`로 로컬 전용.

## ML 코어 아키텍처

### 단일 피처 빌더, 두 개의 계약(contract)

`ml/baseline/preprocess.py`가 **두 모델 모두의 피처 생성을 담당하는 단일 진실 공급원**이다. 두 계약이 같은 파일에 정의된다:

| 계약 | 상수 | 피처 수 | 요원 | diff 피처 | 모델 | 출력 위치 |
|------|------|--------|------|-----------|------|-----------|
| baseline | `FEATURE_COLS` | 178 | 28종 (Miks 제외) | 포함 | LR+DT | `models/baseline/`, `reports/baseline/` |
| advanced | `FEATURE_COLS_ADVANCED` | 125 | 29종 (Miks 포함) | 제외 | RF+XGB+LGBM | `models/advanced/`, `reports/adv_kaggle_only/` |

피처 수는 import 시점에 하드 어서션으로 검증된다 — 178/125에서 벗어나면 `RuntimeError`. 피처 컬럼 집합(map 원핫 + 역할군 count + 요원 count + 선수 prior + synergy + 맵×요원 + 선수×요원)을 바꾸면 이 상수와 어서션을 함께 수정해야 한다. `build_xy(df, feature_contract=...)`가 정규 컬럼 순서로 X/y/groups를 만든다.

**런타임 예측도 같은 빌더를 재사용한다**: `app/predict.py`는 `_history_state_before_year` 등 `ml/baseline/preprocess.py`의 내부 함수를 직접 import해, 커스텀 라인업에 대해 "기준 연도 이전" 히스토리 상태를 다시 계산하고 `_build_feature_row`로 125피처 한 행을 만든다. 즉 학습 피처 로직과 추론 피처 로직이 한 코드 경로를 공유한다.

### 누수 방지가 1급 관심사

모델은 **경기 시작 전(prematch)** 정보만으로 예측하도록 강하게 설계됐다:

- **이전 연도만(previous-year-only)**: 선수/맵×요원/선수×요원 prior 집계는 *현재 경기 연도보다 이전* 연도만 사용. 같은 연도·같은 경기 스탯 제외.
- **리그 평균 스무딩**: 표본이 적은 선수 평균을 이전-연도 리그 평균 쪽으로 수축(`PLAYER_PRIOR_SMOOTHING_GAMES = 5.0`, `RunningStats.smoothed_avg`).
- **금지 피처**: 팀명·점수·승패·라운드·동일경기 스탯·`h2h_wr`/`prior_wr`/`map_wr` 등은 `FORBIDDEN_FEATURE_PATTERNS`/`find_forbidden_feature_names`로 차단. 팀명을 입력받지 않는 UI 구조상 팀 누적 피처는 추론 불가하므로 전면 제거됨.
- **소스 계약**: 학습/평가 행은 `source`가 `kaggle_`로 시작하는 것만. `vlrgg_*`는 피처 생성 전에 제외(`SOURCE_CONTRACT`, `_filter_allowed_sources`).
- **검증 게이트**(`*/validate.py`): 금지 피처 0, split match_key 중복 0, 동일연도 제외 감사, 라벨 셔플 AUC≈0.5, 단일 피처 AUC 스캔, advanced는 test AUC≥0.70. 통과 시 `final_verdict`에 `PASS_TRUSTED_*` 기록.

새 피처를 추가할 때는 반드시 prematch 시점에 알 수 있는 값인지, 금지 패턴에 걸리지 않는지 확인하고 validate를 다시 돌릴 것.

### 헷갈리기 쉬운 세 개의 preprocess 모듈

- `ml/baseline/preprocess.py` — **활성 피처 빌더**. baseline·advanced 두 계약 모두 여기서 나온다. `data/processed/{matches,players}.csv`를 읽어 선수별 이전-연도 집계 생성.
- `ml/advanced/preprocess.py` — **팀명 기반 레거시 빌더**(h2h_wr, prior_wr, map_wr, recent form 등). 금지된 팀 누적 피처를 포함하며 활성 advanced 계약과 무관하다. 활성 advanced는 `ml/baseline/preprocess.py --feature-contract advanced`로 만든다. 혼동 주의.
- `ml/raw_preprocess.py` — VLR.gg raw JSON → 검사용 CSV 변환. 활성 모델 계약과 분리된 리포트 전용(테스트·문서용).

### 도메인 상수

- `ml/agent_roles.py` — 요원→역할군 매핑(29종), `MAP_ORDER`(13맵), 맵별 공격 유리도, 팀/대회 이름 별칭. 대용량 파일(주로 데이터). ELI5 스타일의 매우 상세한 한국어 주석.
- `ml/valorant.py` — `agent_roles`를 재노출하고 정규화 헬퍼 추가(`normalize_agent`/`normalize_map`, `AGENTS_SORTED`, `_agent_col_key` 컬럼키 변환, `compute_rounds`).

### 데이터 수집 (VLR.gg)

활성 모델에는 안 쓰이지만(소스 계약상 제외) 수집 파이프라인이 존재한다: `ml/vlrgg/client.py`(API 클라이언트) → `worker.py`(SQLite 큐 기반 병렬 경기 상세 수집기) → `preprocess.py`(→ `data/processed/vlrgg_matches.csv`).

### Streamlit 앱

`app/main.py`(UI·CSS) + `app/predict.py`(예측 로직). 3개 탭: 커스텀 5v5 / 경기 다시보기(test split replay) / 모델 근거. **advanced 모델만 서빙**한다(`models/advanced/ensemble.joblib`, `n_features_in_`≠125면 거부). 한국어 라벨 매핑은 `app/predict.py` 상단 딕셔너리.

## 웹 스택 아키텍처 (FastAPI + Next.js)

### 백엔드는 모델 로직을 재구현하지 않는다

`valo_web_backend/`(FastAPI)는 `app/predict.py`를 import해 그대로 호출하고 결과 `PredictionResult`를 JSON으로 직렬화만 한다(`services/prediction.py`, `serializers.py`). 즉 **Streamlit 앱과 웹이 동일한 예측을 보장**한다. 라우터: `predict`/`replay`/`options`/`model`/`insights`. 예외→HTTP는 `deps.py`(ValueError→422, FileNotFoundError→503). 실행: `uvicorn valo_web_backend.main:app`. `mock_main.py`는 Python mock 서버(프런트 내부 mock으로 대체돼 현재는 부수적).

### 입력/출력 계약 (SSOT — 어기면 안 됨)

- **입력** `POST /predict`: `{ map, cutoff_year, team_a:[{player,agent}×5], team_b:[…] }`. **선수(player)가 필수** — advanced 모델 피처 다수가 선수의 이전-연도 스탯에서 나오므로 요원만으로는 구동 불가(폐기된 `docs/09_web`가 저지른 실수).
- **출력**: `PredictionResult` 직렬화 — `predicted_winner`/`confidence`/`team_a.win_probability`/`role_counts`/`top_features`(실제 피처 컬럼명+한국어 label)/`explanations`(자연어 근거)/`balance`(구성 결함). replay는 `actual_winner`/`hit` 추가.
- **계약 양쪽**: 백엔드 `valo_web_backend/schemas.py`(Pydantic v2) ↔ 프런트 `valo_web_frontend/src/types/api.ts`(TS). **둘을 항상 함께 수정**하고 `tsc --noEmit`로 검증.
- 요원 29 / 맵 13 / 피처 125는 불변(`ml/`에서 확정).

### 프런트엔드는 자체 mock을 내장 → `npm run dev` 단독 동작

`valo_web_frontend/`(Next.js 16 App Router, React 19, TS, Tailwind v4):
- `src/lib/mock.ts` + `src/app/api/**/route.ts`(8개) = **프런트 내부 mock**. `src/lib/api.ts`의 베이스가 `NEXT_PUBLIC_API_URL ?? "/api"`라, `.env.local`이 `/api`면 모델/백엔드 없이도 전체 UI에 데이터가 뜬다. 실제 백엔드로 전환하려면 `.env.local`의 `NEXT_PUBLIC_API_URL=http://localhost:8000`.
- 페이지: `/`(홈)·`/predict`(커스텀 5v5, FHD 기준 좌측 입력·우측 인사이트+결과 반응형)·`/replay`·`/model`. 컴포넌트는 `components/{predict,insights,result,replay,ui}`.
- **Tailwind v4 함정**: `src/app/globals.css`의 `@theme` 색 토큰이 글꼴 크기 유틸과 충돌할 수 있다. 특히 `--color-base`가 `text-base`(font-size)를 가려 검정 텍스트로 렌더됨 — 테마 색을 `base`/`lg`/`xl` 등 Tailwind 사이즈 단어로 짓지 말 것.
- **Next.js 16 주의**: `valo_web_frontend/AGENTS.md`가 코드 작성 전 `node_modules/next/dist/docs/` 확인을 요구. Route Handler의 `params`는 async(`await params`), Turbopack 기본.

### 인사이트 (요원-맵 적합도 N · 메타 조합 K)

`ml/insights/build_insights.py`가 `matches.csv`를 집계해 `reports/insights/{agent_map_fit,meta_comps}.json` 생성 → 백엔드 `services/insights.py`가 로드(+ `valo_web_backend/data/agent_map_rules.json` 룰 fallback). 모델 추론과 무관(콜드스타트 없음). 구성 결함 경고·자연어 근거는 직렬화 단계(`serializers.py`)에서 생성. 자연어는 현재 `importance×value` 휴리스틱(진짜 SHAP 아님). 상세: `docs_web/06_insights/`.

## 저장소 운영 규칙

- `.gitignore`는 **허용목록(allowlist)** 방식. 커밋되는 것: `app/`·`ml/`·`docs/`·`docs_web/`·`valo_web_backend/`·`valo_web_frontend/`(단 `node_modules/`·`.next/`·`.env*` 제외) + 루트 필수 파일(`README.md`·`requirements.txt`·`dataload.py`·`.gitignore`·`CLAUDE.md`). `data/`·`models/`·`reports/`·`tests/`·`scripts/`·`*.joblib` 등은 모두 로컬 전용 — 학습 산출물·데이터·모델은 저장소에 없다.
- **데이터 블로커**: `data/processed/{matches,players}.csv`를 만드는 Kaggle→processed 변환 스크립트가 저장소에 없다(gitignore된 `scripts/` 추정). 이게 없으면 실제 모델 학습·실제 백엔드 `/predict`/`/replay`가 막힌다. **웹 UI 작업은 프런트 내부 mock으로 우회**하면 데이터 없이 가능.
- 성능 수치(AUC 등)는 코드/문서 값보다 `reports/{baseline,adv_kaggle_only}/metrics.json`을 진실로 본다(재학습마다 소폭 변동). 대략 baseline Test AUC ~0.66, advanced ~0.76.
- 비밀키는 `.env`로만 관리하고 절대 커밋하지 않는다.
