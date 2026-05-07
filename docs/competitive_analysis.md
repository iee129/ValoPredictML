# ValoPredictML 경쟁 차별점 분석

조사일: 2026-05-05  
비교 대상: GitHub/Kaggle/학술 논문에서 수집한 Valorant ML 예측 프로젝트 8개

---

## 1. 경쟁 프로젝트 현황

### 1.1 주요 프로젝트 요약표

| 프로젝트 | 예측 목표 | 주요 모델 | 최고 성능 | 데이터 누수 방지 | UI/배포 |
|----------|-----------|-----------|-----------|-----------------|---------|
| [kleinaitis/valorant-match-predictor](https://github.com/kleinaitis/valorant-match-predictor) | 일반 랭크 게임 승패 | 비공개 | **미공개** | 불명확 | PyInstaller 실행파일 |
| [jasonlow2307/valo-prediction](https://github.com/jasonlow2307/valo-prediction) | 실시간 라운드/매치 승패 | CNN + RF | Acc **96%** ⚠️자가보고 | 불명확 | Matplotlib 실시간 |
| [Juniorffonseca/valorant-predictor](https://github.com/Juniorffonseca/valorant-predictor) | 프로 씬 매치 승패 | Neural Network | **미공개** | 부분적 | Flask API |
| [lucaspellegrinelli/valorant-agent-embeddings](https://github.com/lucaspellegrinelli/valorant-agent-embeddings) | 팀 구성 요원 임베딩 학습 | BERT 오토인코더 | **미공개** | N/A (생성 문제) | 없음 |
| [DEF4LT-303/Valorant-Pro-Match-Analysis](https://github.com/DEF4LT-303/Valorant-Pro-Match-Analysis) | 토너먼트 우승 팀 예측 | Decision Tree + RF | Acc **93%** ⚠️train=1.0 과적합 | 없음 | 없음 |
| [Pawar/NCI 석사 논문](https://norma.ncirl.ie/8770/) | 프로 매치 승패 + 베팅 시뮬레이션 | XGBoost 앙상블 | Acc **73%** | 불명확 | 프로토타입 |
| [TechRxiv — Economy & Ultimate](https://www.techrxiv.org/users/916972/articles/1289732) | 라운드 경제력 기반 승패 | Logistic Regression | Acc **60.6%** | 부분적 | 없음 |
| [arXiv 2510.17199](https://arxiv.org/abs/2510.17199) | 비디오 미니맵 기반 라운드 승패 | TimeSformer | Acc **80.6%** / 후반 **90.6%** | 명시적 시간 분리 | 없음 |

> ⚠️ **자가보고**: 검증 방법론이 공개되지 않아 재현 불가능  
> ⚠️ **과적합 의심**: train accuracy=1.0은 데이터 누수 또는 과적합의 강한 신호

### 1.2 ValoPredictML 기준선

| 지표 | 값 | 출처 |
|------|-----|------|
| Ensemble Test AUC | **0.9355** | `reports/eval_summary.json` |
| Ensemble Test Acc | **0.8540** | `reports/eval_summary.json` |
| Ensemble Test F1 | **0.8508** | `reports/eval_summary.json` |
| K-Fold Ensemble AUC | **0.9414** | `reports/eval_summary.json` |
| K-Fold vs Test gap | **0.0059** | AUC 기준, 과적합 없음 (기준 0.01 미만) |
| Majority baseline 대비 | **+29.1%p** | `reports/baseline_comparison.json` |
| 학습 데이터 규모 | **66,485 clean행** | `reports/preprocess_summary.json` |
| 피처 수 | **45개** | `reports/preprocess_summary.json` |

---

## 2. 핵심 차별점 (5개)

### 2.1 방법론적 엄밀성 — 데이터 누수 완전 차단

**구현**: `ml/evaluate_model.py:51`

```python
groups = df_train["match_key"].str.replace(r"_swap$", "", regex=True)
```

- **무엇**: GroupKFold(5)에서 match_key 기준으로 경기 단위 폴드 분리. A/B swap 증강 쌍이 서로 다른 fold에 들어가는 것을 `_swap` suffix 제거로 방지.
- **왜 중요**: 동일 경기의 증강 쌍이 train/val에 분리되면 eval 성능이 인위적으로 높아짐. DEF4LT-303의 train=1.0은 이 처리 없이 발생한 전형적 결과.
- **비교**: 8개 프로젝트 중 이 수준의 누수 방지를 명시적으로 구현한 프로젝트는 0개 (arXiv 논문은 시간적 분리만, 경기 단위 분리 없음).

### 2.2 멀티소스 SHA-1 dedup — 교차 소스 중복 자동 제거

**구현**: `ml/data_pipeline.py:67`, `ml/data_pipeline.py:613-617`

```python
def make_dedup_key(date, event, map_norm, team_a, team_b, agents_a, agents_b, score_a, score_b):
    # SHA-1 기반 24자 hex — 동일 경기가 여러 Kaggle 소스에 존재해도 자동 제거
```

- **검증된 효과**: Paris 2025 + Stage 2 2025 데이터셋 추가 시 450 raw행 → 전량 `DEDUP_LOW_WEIGHT` 탈락 (vct-2025-all-events와 완전 중복 자동 감지). `reports/dataset_expansion_comparison.md` 참조.
- **소스 가중치** (`ml/data_pipeline.py:27-32`): 중복 시 고품질 소스 우선 보존 — challengers=1.8, vct/qualidea=1.0, ediashtarevin=0.9 (~~piyush=1.5 — 소스 제거됨~~)
- **비교**: 단일 Kaggle 데이터셋만 사용하는 프로젝트들은 이 문제를 아예 고려하지 않음.

### 2.3 도메인 특화 피처 — 27개 요원 × 역할 분류

**구현**: `ml/agent_roles.py`, `ml/data_pipeline.py:36-54`

피처 체계:
- **역할 카운트**: `a_duelist`, `a_initiator`, `a_controller`, `a_sentinel` (팀 A 역할별 인원)
- **역할 차이**: `diff_duelist`, `diff_initiator`, `diff_controller`, `diff_sentinel` (A-B 차이)
- **역할 더미**: `has_controller_a/b`, `double_duelist_a/b` (전략적 구성 패턴)
- **맵 인코딩**: 12개 맵 × 공격 우위 매핑 (`map_encoded`)

27개 요원 (2026년 기준 최신): Duelist 8종 · Initiator 7종 · Controller 6종 · Sentinel 6종

- **비교**: jasonlow2307는 실시간 화면 분석, TechRxiv는 경제력/얼티밋 포인트만 사용. 요원 역할 체계를 피처로 모델링한 프로젝트는 이 조사에서 ValoPredictML이 유일.

### 2.4 검증된 앙상블 + Optuna HPO

**구현**: `ml/train_model.py:132-251`

- **3중 앙상블**: RF(n_estimators=300) + XGBoost(500, max_depth=5, lr=0.05) + LightGBM(500, num_leaves=31, lr=0.05), 단순 평균 (1/3씩)
- **Optuna HPO**: XGBoost는 max_depth·min_child_weight·gamma·lr·colsample_bytree, LightGBM은 num_leaves·min_child_samples·lr를 GroupKFold(5) 기반 AUC 최적화 + MedianPruner로 튜닝

| 모델 | K-Fold AUC | Test AUC |
|------|-----------|---------|
| RF | 0.9449 | 0.9378 |
| XGBoost | 0.9343 | 0.9281 |
| LightGBM | 0.9353 | 0.9292 |
| **Ensemble** | **0.9414** | **0.9355** |

- **비교**: Pawar 논문의 XGBoost 앙상블(Acc 73%)은 성능에서 크게 하회. DEF4LT-303은 단일 RF (train=1.0, 과적합).

### 2.5 경기 전 팀 구성 기반 사전 예측

- **예측 입력**: 경기 시작 전 양 팀의 요원 구성 (5v5) + 맵
- **예측 출력**: 팀 A 승률 (0~1 확률)
- **외부 데이터 불필요**: 실시간 게임 캡처, 라운드별 경제력, API 연결 없음

이 포지셔닝은 다른 프로젝트들과 정확히 직교합니다:
- jasonlow2307: 실시간 화면 캡처 → 라운드 내 승률 (경기 중 사용)
- TechRxiv: 경제력·얼티밋 포인트 → 라운드 예측 (경기 중)
- arXiv: 비디오 미니맵 분석 → 라운드 예측 (방송 분석용)
- **ValoPredictML**: 팀 구성만으로 → 경기 전 확률 (경기 전 사용, 피킹 단계)

---

## 3. ValoPredictML이 뒤처지는 영역 (정직한 약점)

### 3.1 UI 미구현 — 가장 큰 약점

kleinaitis는 PyInstaller로 패키징된 실행파일을 배포하고, jasonlow2307는 Matplotlib 실시간 대시보드를 제공합니다. ValoPredictML은 ML 파이프라인만 완성됐고 **Streamlit UI는 미구현** 상태입니다.

→ 현재 상태: CLI(`ml/validate_metrics.py`)로만 결과 확인 가능.

### 3.2 일반 랭크 게임 적용 불가

데이터 소스가 전부 프로/준프로 경기(VCT, Challengers League)입니다. 일반 랭크 게임(솔로큐)에 적용 시 성능 저하 예상. kleinaitis는 tracker.gg 기반으로 일반 게임도 지원합니다.

### 3.3 메타 변화에 취약

현재 모델은 정적 학습 데이터 기반입니다. 패치로 요원 밸런스가 크게 변할 경우 재학습 없이는 성능 저하. 실시간 업데이트 메커니즘이 없습니다.

---

## 4. 성능 신뢰도 평가

| 프로젝트 | 보고 성능 | 신뢰도 | 이유 |
|----------|-----------|--------|------|
| **ValoPredictML** | AUC=0.935, Acc=0.854 | **높음** | GroupKFold 교차검증 + hold-out test set 분리 + 재현 가능한 파이프라인 |
| jasonlow2307 | Acc=96% | **낮음** | 검증 방법론 미공개, 자가보고, 재현 불가 |
| DEF4LT-303 | Acc=93% | **낮음** | train=1.0 (과적합 명백), 누수 처리 없음 |
| Pawar/NCI | Acc=73% | **중간** | 석사 논문 수준, 합성 데이터(CTGAN)로 학습셋 보강 |
| arXiv 2510.17199 | Acc=80.6% / 90.6% | **높음** | 동료 검토 예정 논문, 시간적 데이터 분리 명시, 단 다른 예측 목표 |
| TechRxiv | Acc=60.6% | **높음** | 통계적 유의미(p≈0.000), 단 단순 모델, 다른 예측 목표 |

---

## 5. 포지셔닝 결론

**ValoPredictML의 포지셔닝**: "방법론적으로 엄밀한, 경기 전 팀 구성 기반 프로 씬 승률 예측기"

| 구분 | 내용 |
|------|------|
| 대상 사용자 | Valorant 프로 씬/스크림 분석가, 팀 코치, 팀 구성 연구자 |
| 핵심 가치 | 피킹 단계에서 팀 구성 승률을 검증된 방법으로 예측 |
| 기술적 강점 | 데이터 누수 방지 + 멀티소스 dedup + 도메인 피처 + 앙상블 |
| 현재 한계 | UI 미구현, 일반 랭크 적용 불가 |
| 다음 단계 | Streamlit UI 구현 → 실제 사용 가능한 도구로 전환 |

