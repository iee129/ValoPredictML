# ML 개념 검증 — ValoPredictML

기반: `src/ml/baseline/evaluate.py`, `src/ml/baseline/train.py`, `src/ml/advanced/evaluate.py`, `src/ml/advanced/feature_importance.py`
데이터: baseline `data/processed/`, advanced `data/processed/advanced/`
결과: `reports/advanced/metrics.json`, `reports/advanced/validation.json`

본 프로젝트는 베이스라인 1개(LR+DT, 랜덤 80/20, 421피처) + 심화 1개(RF+XGB+LGBM, 시간순 holdout, 179피처) 2개 모델을 비교한다.

---

## 1. GroupKFold 선택 근거

### 문제: 같은 경기가 학습과 평가에 동시에 들어가는 상황

Valorant 경기 데이터는 **같은 경기(match_key)에서 복수 행이 생성**된다.  
한 경기(match_key)가 복수의 맵 행을 포함하므로, 무작위 분할 시 같은 경기의 맵 행이 train과 validation에 동시에 들어갈 수 있다.

random split 또는 StratifiedKFold를 사용하면:
- 같은 match_key의 맵 1이 train fold, 맵 2가 validation fold에 들어갈 수 있음
- 모델이 "같은 경기"의 다른 맵을 이미 학습한 상태에서 검증 → 낙관적 estimate

### 해결: GroupKFold(n_splits=5, groups=match_key)

```python
# src/ml/baseline/evaluate.py
gkf = GroupKFold(n_splits=n_splits)
groups = df_train["match_key"]
```

`match_key`를 그룹으로 지정해 같은 경기의 모든 맵 행이 **항상 같은 fold**에 배정된다.  
GroupKFold는 같은 group을 절대 다른 fold에 분리하지 않으므로 같은 경기가 학습·평가에 섞이는 일이 구조적으로 차단된다.

### 선택 근거 요약

| 기법 | 문제 |
|------|------|
| KFold | 경기 행 무작위 분리 → match_key 겹침 |
| StratifiedKFold | 클래스 비율 보존은 하지만 match_key 겹침 그대로 |
| **GroupKFold** | match_key 단위 분리 → 겹침 없음, 실제 배포 환경 시뮬레이션 |

test.csv는 K-Fold 중 절대 사용하지 않는다. 최종 평가 1회만 사용한다.

### 추가 안전장치

- **금지 피처 26개 정규식 차단**: `find_forbidden_feature_names()`이 미래 정보 피처(예: 최종 라운드 스탯 등)를 학습 전 자동 제외
- **prior 집계는 이전 연도만**: `agent_map_stats` 집계 시 `year < current_year` 조건으로 미래 경기 통계 사용 금지
- **리그 평균 smoothing**: `RunningStats.smoothed_avg()`로 소표본 노이즈 억제

---

## 2. 앙상블 전략 — 편향-분산 트레이드오프

### 세 모델의 특성

| 모델 | 알고리즘 | 편향 | 분산 | Test AUC (시간순) |
|------|----------|------|------|----------|
| RF | Bagging (트리 평균) | 낮음 | **낮음** | 0.6965 |
| XGBoost | Boosting (순차 잔차 학습) | 더 낮음 | 중간 | 0.7007 |
| LightGBM | Boosting (leaf-wise) | 더 낮음 | 중간 | **0.7015** |
| **Ensemble** | Soft Voting (가중 2.0:3.0:0.1) | — | — | **0.7010** |

### 앙상블 방식 (Soft Voting)

```python
# src/ml/advanced/ensemble.py — RF/XGB/LGBM 확률을 가중 평균(2.0:3.0:0.1)으로 결합
```

### 단일 모델보다 앙상블을 쓰는 이유

세 트리 모델의 Test AUC가 0.6965~0.7015로 근접하지만 앙상블을 선택한 이유:

1. **오류 독립성**: Bagging(RF)과 Boosting(XGB/LGBM)의 오류 패턴이 다르다.  
   서로 다른 방식으로 틀리기 때문에 평균 시 상쇄된다.
2. **분산 감소**: 단일 Boosting 모델은 하이퍼파라미터에 민감하다. 가중 soft voting으로 안정성 확보.
3. **고정 하이퍼파라미터**: Optuna는 사용하지 않고, 각 모델은 코드에 고정된 하이퍼파라미터로 학습한 뒤 Soft Voting으로 결합한다.

---

## 3. 피처 중요도 도메인 해석

### 중요도 계산 방식

피처 중요도는 `src/ml/advanced/feature_importance.py`에서 트리 모델의 `feature_importances_`로 산출하고, 자연어 근거는 직렬화 단계(`serializers.py`)에서 `importance × value` 휴리스틱으로 생성한다. **진짜 SHAP 값이 아니다.**

### 중요도 일관성

RF·XGBoost·LightGBM의 상위 중요도 피처는 거의 같다. 세 모델 모두 선수의 이전 연도 prior(출전 경험·KD·ADR) 계열을 공통으로 상위에 올린다. 서로 다른 알고리즘이 같은 피처군을 중요하게 보므로 피처 중요도 해석의 신뢰성이 높다.

### 도메인 지식과의 일치

상위 중요도 피처는 선수의 이전 연도 prior 계열(`prior_games`, `prior_kd`, `prior_adr`)과 synergy다. 이를 Valorant 도메인 지식으로 해석하면:

- **이전 출전 경험 (`prior_games`)**: 누적 출전이 많은 선수일수록 prior 추정이 안정적이며, 팀 전력의 기준점이 된다.
- **이전 교전 성과 (`prior_kd`, `prior_adr`)**: KD(처치/사망 비)와 ADR(라운드당 피해)은 선수의 교전 기여를 요약한다. 이전 시즌 성과가 다음 경기 전력 추정에 반영된다.
- **synergy**: 같은 선수 조합이 이전에 함께 거둔 성과로, 역할 조합뿐 아니라 손발이 맞는 정도를 포착한다.

---

## 4. 데이터 분할 및 피처 계약

### 데이터 경로 및 분할

| 모델 | 데이터 경로 | 분할 방식 |
|------|-----------|----------|
| 베이스라인 | `data/processed/` | match_key 랜덤 80/20 |
| 심화 | `data/processed/advanced/` | 연도 블록 시간순 (train 2020–2025 / test 2026, 맵 단위 승패 샘플) |

분할 방식이 모델마다 다르다 — 베이스라인은 전 기간을 무작위 80/20으로, 심화는 2026년을 test로 둔 시간순 split으로 나눈다.

### 피처 수

| 파이프라인 | 피처 수 | 주요 내용 |
|-----------|---------|---------|
| Baseline | **421** | 슬롯 400(10명 × [PRIOR 8 + 요원 27 + 역할 5]) + 컨텍스트 21(맵 12 + synergy 3 + 역할조합 6) |
| Advanced | **179** | 선별 피처 (`data/processed/advanced/` feature contract) |

---

## 5. 알고리즘 선택 적합성

### 이진 분류가 적합한 이유

이 문제는 **승리(1) / 패배(0)** 레이블로 정의된다. 확률적 해석(팀 A가 이길 확률 p%)이 필요하므로 이진 분류가 자연스럽게 적합하다.

### 왜 로지스틱 회귀가 아닌가

로지스틱 회귀는 피처 간 **선형 상호작용**을 가정한다. 그러나 이 데이터에서:

- `a_initiator × a_controller` 조합 효과 — Initiator가 많아도 Controller 없으면 구역 통제 불가
- `diff_initiator × map_encoded` — 맵별로 같은 역할 차이가 다른 승률 기여를 가짐

이러한 비선형 역할 상호작용은 로지스틱 회귀로 포착하기 어렵다. 트리 기반 모델은 분기(split)를 통해 이런 상호작용을 자동으로 학습한다.

### 왜 딥러닝이 아닌가

딥러닝은 **대용량 데이터(수백만 행 이상)** 와 비정형 데이터(이미지·텍스트)에서 강점을 발휘한다.  
이 프로젝트는 **표 형태 데이터** 로, 학계와 실무 모두 이 규모에서는 트리 기반 앙상블을 표준 선택으로 권장한다.

### RF / XGB / LightGBM의 역할과 보완 관계

| 모델 | 알고리즘 | 주된 역할 | Test AUC (시간순) |
|------|----------|-----------|---------|
| **RF** | Bagging (트리 평균) | **분산 감소** — 과적합 내성 | 0.6965 |
| **XGBoost** | Boosting (순차 잔차 학습) | **편향 감소** — 연속형·순서형 피처 처리 강점 | 0.7007 |
| **LightGBM** | Boosting (leaf-wise) | **편향 감소** — 대용량·고차원에서 빠른 학습 | 0.7015 |
| **Ensemble** | Soft Voting (2.0:3.0:0.1) | 오류 독립성으로 추가 분산 감소 | **0.7010** |

앙상블의 오류 독립성과 분산 감소 효과는 §2에서 설명된다.

---

## 성과 지표 요약

### Baseline (LR+DT Soft Voting 0.50/0.50, 421피처, 랜덤 80/20)

| 지표 | LR | DT | 앙상블 |
|------|----|----|--------|
| ROC-AUC | 0.6000 | 0.5556 | **0.5943** |
| Accuracy | 0.5821 | 0.5483 | **0.5667** |
| F1 | 0.6216 | 0.5860 | **0.6072** |

majority 기준선 대비 +0.0649. 출처: 발표자료(PDF) 베이스라인 보고값.

### Advanced (RF+XGB+LGBM Soft Voting 2.0:3.0:0.1, 179피처, 시간순)

| 지표 | Test (Ensemble) | RF | XGB | LGBM |
|------|----------------|-----|-----|------|
| ROC-AUC | **0.7010** | 0.6965 | 0.7007 | 0.7015 |
| Accuracy | **0.6454** | — | — | — |
| F1 | **0.6478** | — | — | — |

출처: `reports/advanced/metrics.json`

상세 수치 출처: `src/ml/advanced/evaluate.py`, `src/ml/advanced/validate.py`
