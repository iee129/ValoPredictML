# 01. 목적과 범위

## 1. 목적

학습 파이프라인(`ml/`)으로 만든 **advanced 앙상블 모델**(125피처 RF+XGB+LGBM)을 FastAPI로 서빙하고, **Next.js 16 (TypeScript)** 프론트엔드에서 호출해 **모델 동작을 UI로 시연**한다.

시연의 핵심 사용자 흐름:

```
맵 선택 + 기준 연도 선택
  → 팀 A 5명(선수+요원) 입력 + 팀 B 5명(선수+요원) 입력
  → [예측] 클릭
  → 승률 게이지 + 신뢰도 + 역할군 구성 + 영향 피처 표시
```

부가 시연 흐름:
- **경기 다시보기(replay)**: test split의 실제 경기를 골라 예측 vs 실제 결과 대조 (가장 빠른 데모 경로 — 피처가 이미 계산돼 있음)
- **모델 근거**: 모델 메타(125피처, 알고리즘), test AUC/정확도, 검증 verdict, 전역 피처 중요도 표시

---

## 2. 왜 입력에 "선수"가 반드시 필요한가 (09_web과 갈린 지점)

advanced 모델의 125피처 중 다수가 **선수의 이전 연도 누적 스탯**에서 나온다(`a_prior_kd_mean`, `a_player_agent_*_mean`, `a_synergy_mean` 등). 즉 모델은 "요원 5개"만으로 동작하지 않으며, **각 슬롯의 선수 식별자**가 있어야 시스템이 `data/processed`에서 이전 연도 스탯·동반출전 이력을 조회한다.

`docs/09_web`의 `/predict`는 `team_a: ["Jett", ...]`처럼 **요원 이름만** 보냈다. 이는 실제 모델 입력 계약(`predict_custom_lineup(map_name, cutoff_year, team_a_slots, team_b_slots)`, slot = `{player, agent}`)과 맞지 않아 그대로는 구동 불가능하다. 본 문서는 이를 바로잡는다.

근거 코드: `app/predict.py`의 `_slot_to_player_input`, `_custom_feature_frame`, `ml/baseline/preprocess.py`의 `_build_feature_row`.

---

## 3. 범위

### 포함 (In scope)

| 항목 | 내용 |
|------|------|
| 백엔드 | FastAPI 단일 서비스. `app/predict.py` 재사용. 모델 로직 재구현 없음 |
| 모델 | advanced 125피처 앙상블 1종만 서빙 (`models/advanced/ensemble.joblib`) |
| 엔드포인트 | `/predict`, `/replay/*`, `/options`, `/agents`, `/maps`, `/players`, `/years`, `/model`, `/health` |
| 프론트 | Next.js 16 App Router + React 19 + **TypeScript** |
| 페이지 | `/predict`(커스텀 5v5), `/replay`(경기 다시보기), `/model`(모델 근거) |
| 시각화 | 승률 게이지, 역할군 레이더, 영향 피처 바 |

### 제외 (Out of scope)

| 항목 | 사유 |
|------|------|
| 예측 기록 DB(PostgreSQL) | `README.md`·`docs/03_architecture/03_database_schema.md` 기준 범위 외. 시연에 불필요 |
| `/history` · `/analytics` 영속 집계 | 위와 동일. 필요 시 in-memory/JSON로 선택 구현 가능(본 문서는 선택 항목으로만 언급) |
| baseline 178피처 모델 | 앱은 advanced만 서빙 (`app/predict.py` 고정) |
| Vercel 프로덕션 배포 | 시연은 로컬(`localhost:3000` ↔ `localhost:8000`) 우선. 배포는 선택 |
| 인증 | 공개 시연 API, 인증 없음 |
| 모델 재학습/HPO | 본 문서는 "서빙·연동"만 다룸. 학습은 `ml/` 파이프라인 소관 |

---

## 4. 전제 조건 (시연 전 준비물)

FastAPI가 로드하는 산출물은 모두 `.gitignore`로 로컬 전용이다. 시연 전에 학습 파이프라인을 먼저 돌려 아래가 존재해야 한다:

```
models/advanced/ensemble.joblib          # POST /predict, /replay
models/advanced/meta.json                # GET /model
reports/adv_kaggle_only/metrics.json     # GET /model (test AUC 등)
reports/adv_kaggle_only/validation.json  # GET /model (verdict)
data/processed/matches.csv, players.csv  # /predict 런타임 피처 계산, /options
data/processed/adv_kaggle_only/test.csv  # /replay 후보 + /options replay
```

생성 절차는 [../04_integration/02_demo_runbook.md](../04_integration/02_demo_runbook.md) 참조.

---

## 5. 관련 문서

- 아키텍처 상세 → [02_architecture.md](02_architecture.md)
- 기술 스택/버전 → [03_tech_stack.md](03_tech_stack.md)
- 데이터 계약 SSOT → [../04_integration/01_data_contract.md](../04_integration/01_data_contract.md)
