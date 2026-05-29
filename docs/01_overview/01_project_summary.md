# 01. 프로젝트 소개 및 핵심 아이디어

마지막 업데이트: 2026-05-27

## 1. ValoPredictML이란?

**ValoPredictML**은 FPS 게임 Valorant의 **5v5 팀 조합**을 입력받아 **승률을 예측**하는 머신러닝 기반 **Streamlit 로컬 분석 도구**입니다.

픽 단계(경기 시작 전 요원 선택 단계)에서 양 팀의 라인업(선수 5명 + 요원 5명)을 분석하고, Streamlit 화면에서 예측 결과와 영향 피처를 확인합니다.

> **라인업**: 선수 5명 + 각 선수의 요원 픽 전체. 이 프로젝트의 핵심 입력 단위.

| 항목 | 기준 |
|------|------|
| 제품 형태 | Streamlit 기반 로컬 분석 도구 |
| 핵심 흐름 | 조합 입력 → 승률 예측 → 영향 피처 확인 → 교체 시뮬레이션 |
| 현재 구현 | baseline 178피처(`ml/baseline/`, Test AUC 0.6587) + advanced 125피처 앙상블(`ml/advanced/`, Test AUC 0.7570, Optuna+SHAP) + Streamlit UI(`app/`) 모두 구현 완료 |
| 제외 | FastAPI, React/Next.js, 클라우드 배포, 외부 API — 사용 안 함 |

---

## 2. 문제 정의

### 2.1 배경

Valorant는 29종 (2026-03 기준)의 요원(캐릭터) 중 각 플레이어가 1명씩 선택하여 5v5로 대결하는 게임입니다.
요원 선택 단계(픽창)에서 팀 구성은 승패에 중요한 영향을 미치지만,
어떤 조합이 유리한지 데이터 기반으로 파악하기 어렵습니다.

### 2.2 해결하려는 것

> **"지금 이 팀 조합으로 싸우면 이길 가능성이 얼마나 될까?"**

맵 + 선수 5명 + 요원 5명 (팀당)을 입력하면, 머신러닝 모델이 승률을 계산해주는 로컬 도구를 구축합니다.

---

## 3. 핵심 아이디어: 역할군 기반 피처 추상화

### 3.1 개별 요원 접근법의 문제

27종 요원을 각각 One-Hot Encoding으로 피처화하면: (당시 27종 기준 예시, 현재는 29종)
- 피처 수: 27 × 2팀 = **54개** (고차원, 과적합 위험)
- 신규 요원 출시 시: **모델 재학습 필수** (운영 부담)
- 데이터 부족: 최근 출시 요원은 경기 수가 적어 **학습 신뢰도 저하**

또한 팀명 기반 누적 이력 피처(`h2h_wr`, `prior_wr`, `map_wr` 등)는 UI에서 팀명을 입력받지 않는 본 프로젝트 구조에서는 추론 불가하므로 모두 제거됨.

### 3.2 역할군 카운트 접근법

모든 요원을 4대 역할군으로 분류합니다:

| 역할군 | 영어 | 역할 | 예시 요원 |
|--------|------|------|-----------|
| 타격대 | Duelist | 공격적 진입, 킬 창출 | Jett, Reyna, Neon |
| 척후대 | Initiator | 정보 수집, 팀 진입 보조 | Sova, Breach, Fade |
| 전략가 | Controller | 스모크로 시야 차단, 지역 통제 | Viper, Omen, Astra |
| 감시자 | Sentinel | 수비, 사이드 잠금, 힐 | Killjoy, Cypher, Sage |

**피처 추출 방식:**
```
팀 A: [Jett(D), Sova(I), Viper(C), Killjoy(S), Skye(I)]
→ a_duelist=1, a_initiator=2, a_controller=1, a_sentinel=1

팀 B: [Reyna(D), Breach(I), Omen(C), Cypher(S), Fade(I)]
→ b_duelist=1, b_initiator=2, b_controller=1, b_sentinel=1
```

### 3.3 178개 피처 구성 (baseline)

| 카테고리 | 피처 수 | 설명 |
|----------|---------|------|
| 맵 원핫 | 13 | `map_ascent` ~ `map_corrode` |
| 역할군 count | 12 | 4역할군 × (A, B, A-B 차이) |
| 28명 요원 count | 84 | 28요원 × (A, B, A-B 차이) |
| 선수 이전 연도 prior smoothed 평균 | 24 | prior_games + 7스탯(kd·kast·adr·apr·fkpr·fdpr·clutch) × (A, B, 차이) |
| Synergy (페어 동반출전) | 3 | 팀별 페어 평균 + A-B 차이 |
| 맵×요원 prior smoothed 평균 | 21 | 7스탯 × (A, B, 차이) |
| 선수×요원 prior smoothed 평균 | 21 | 7스탯 × (A, B, 차이) |
| **합계** | **178 + 1 레이블** | |

> advanced 계약은 diff 피처를 빼고 29요원(Miks 포함)을 써 **125피처**다 (`FEATURE_COLS_ADVANCED`).

세부 명세: [../04_data_processing/06_feature_engineering.md](../04_data_processing/06_feature_engineering.md)

### 3.4 이 방식의 장점

| 항목 | 기존 명세 (43) | 현재 baseline (178) |
|------|--------------|------------|
| 입력 단위 | 팀 라인업 + 팀명 | 맵 + 선수명 + 요원 (팀명 X) |
| 팀명 혼입 위험 | h2h_wr 등 팀명 누적 피처 다수 | 팀명 혼입 0건 |
| 슬롯 순서 의존성 | — | 팀별 mean 집계로 순서 불변 |
| UI 추론 가능성 | 팀명 매핑 필요 → 불가 | 선수명만으로 자동 조회 가능 |

---

## 4. 입출력

### 입력

| 구분 | 항목 |
|------|------|
| 사용자 입력 | 맵 1개, 팀A 선수명 5개, 팀A 요원 5개, 팀B 선수명 5개, 팀B 요원 5개 (총 21개 항목) |
| 시스템 자동 조회 | 현재 경기 연도보다 이전 연도의 선수 이력, 선수 페어별 동반 출전 횟수 |
| 시스템 생성 | 맵 원핫, 역할군/요원 count, 팀별 player prior mean, Synergy 팀 평균 |

> **팀명은 입력하지 않음.** 선수명만으로 시스템이 DB에서 스탯·동반출전을 자동 채운다.

### 출력 (Streamlit UI 구현 시 제공)

| 출력 | 설명 |
|------|------|
| 승리 확률 | 팀 A 승률 (이진 분류 확률값) |
| 주요 영향 피처 | feature importance 또는 SHAP |
| 선수-요원 적합도 | 특정 선수+요원 조합의 예상 기여도 |
| 교체 변화량 | 선수/요원 교체 전후 예측 확률 차이 |
| 맵별 최적 요원 조합 | 해당 맵에서 best인 요원 5명 도출 |
| 최정예 로스터 | 최고의 선수 조합, 키 플레이어 식별 |
| 맵 통계 | 요원 픽률, 요원별 승률, 공격/수비 유리도 시각화 |

---

## 5. 성능 (현재 활성 산출물)

| 지표 | Baseline (178) | Advanced Ensemble (125) | 검증 방법 |
|------|---:|---:|----------|
| ROC-AUC (CV) | 0.6599 ± 0.0016 | — | train GroupKFold (K=5) by `match_key` |
| ROC-AUC (test) | 0.6587 | 0.7570 | 홀드아웃 `test` (80/20 랜덤) |
| Test accuracy | 0.6290 | 0.6958 | metrics.json |
| Test F1 | 0.7231 | 0.7649 | metrics.json |
| Trust verdict | `PASS_TRUSTED_PREMATCH_BASELINE` | `PASS_TRUSTED_KAGGLE_ONLY_ADVANCED` | validation.json |

출처: `reports/baseline/metrics.json`, `reports/adv_kaggle_only/metrics.json`. advanced 0.7570은 80/20 match_key 랜덤 holdout(train 53,427 / test 13,357) 기준이며 시간순 미래 예측 성능이 아니다 — 상세 해석: [../05_data_learning/03_advanced_models/02_advanced_metric_analysis.md](../05_data_learning/03_advanced_models/02_advanced_metric_analysis.md).

### 개발 원칙

1. 딥러닝(PyTorch, TensorFlow) 금지 — Tabular 데이터 기반 Tree-based 머신러닝만 사용
2. API Key 및 비밀번호는 `.env` 환경변수로 관리, GitHub 커밋 절대 금지

---

## 6. 사용자 측면 차별점 (10개)

지도교수 2차 면담(2026-05-25) 피드백 — **기술적 차별점이 아닌 사용자가 체감하는 차별점을 강화하라** — 에 따라 2주(5/28~6/8) 동안 10개 사용자 차별점을 Streamlit 단일 도구 안에 통합한다. 시장 빈자리는 [../competitive_analysis.md](../competitive_analysis.md) 결론 7.1, 데이터원 매핑은 [../07_data/02_primary_datasets/04_vlrgg.md](../07_data/02_primary_datasets/04_vlrgg.md) 참조.

### 6.1 그룹별 5개 차별점 (2026-05-28 축소 결정)

원래 10개 차별점 설계안에서 (a) 외부 데이터 의존 위험 (b) 학기 일정 우선순위 (c) UI 표시 실현 난이도를 종합 판정해 5개로 확정. 제외: I 카운터 픽 경고 (라운드 능력 이벤트 데이터 부재), B 박빙 검증 (학기 후순위), J Ult Cycle (도메인 룰만으로 가치 약함), A What-if (학기 일정 외), E 사이드 패널 (VLR.gg team stats 의존 위험).

| 그룹 | # | 차별점 | 핵심 산출 | 동력 | VLR.gg 의존 |
|------|---|--------|-----------|------|-------------|
| **1. 픽 단계 입력 즉시 피드백** | N | 맵 메타 적합도 | 슬롯별 ✓/△/✗ 배지 | 룰 (agents.md) | ✗ |
| | K | 메타 조합 매칭률 | 매칭률 % + 권장 메시지 | 룰 (maps.md) | ✗ |
| | G | 조합 밸런스 경고 | Controller 0/Sentinel 과다 등 경고 | 룰 (5개 코드 내장) | ✗ |
| | D | 주력 요원 이탈 알림 (30/60/90일) | out-of-pool 알림 + 도넛 차트 | 외부 API + CSV fallback | ✓ |
| **2. 예측 결과 해석** | C | 승부 근거 카드 (자연어 설명) | SHAP → 한국어 템플릿 카드 | 모델 출력 + 템플릿 | ✗ |

### 6.2 시장 빈자리 4개에 대한 응답

`docs/competitive_analysis.md` 가 식별한 발로란트 도구 시장 4가지 빈자리 중 3개에 대응한다. #2(What-if)는 학기 일정 외로 차기 작업으로 이월.

| 빈자리 | 본 프로젝트의 대응 |
|--------|---------------------|
| 1. prematch 모델 기반 승률 예측 | 베이스라인(Test AUC 0.6587, 완료) + 심화 앙상블(Test AUC 0.7570, 완료) + VLR.gg 통합(예정) |
| 2. What-if 시뮬레이션 | 학기 일정 외 — 차기 작업으로 이월 |
| 3. 자연어 예측 근거 | **C** |
| 4. 개인화 (선수 풀·약점 기반) | **D** ★ + **G·N·K** 도메인 보조 |

### 6.3 기술 차별점 (보조)

사용자 차별점의 기반이 되는 기술 차별점은 [../06_model_test/project_differentiation.md](../06_model_test/project_differentiation.md) 5개 항목으로 별도 관리: 역할 조합 단위 피처 / 이전 연도 prior + 리그평균 smoothing / GroupKFold로 데이터가 섞이지 않게 분할 / SHAP / Optuna HPO.

---

## 7. 관련 문서

| 문서 | 내용 |
|------|------|
| [02_tech_stack.md](02_tech_stack.md) | 기술 스택 상세, 버전, 선택 이유 |
| [03_design_principles.md](03_design_principles.md) | 방어적 처리, 모듈형 아키텍처 등 설계 원칙 |
| [04_roadmap_and_team.md](04_roadmap_and_team.md) | 단계별 로드맵 + 5/28~6/9 일정, 팀 구성, 용어 사전 |
| [../competitive_analysis.md](../competitive_analysis.md) | 발로란트 도구·연구·LoL/Dota 비교, 시장 빈자리 4개 분석 |
| [../06_model_test/project_differentiation.md](../06_model_test/project_differentiation.md) | 5개 기술 차별점 + 10개 사용자 차별점 검증 |
| [../03_architecture/01_system_overview.md](../03_architecture/01_system_overview.md) | 시스템 아키텍처 전체 |
