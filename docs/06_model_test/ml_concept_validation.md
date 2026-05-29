# ML 개념 검증 — ValoPredictML

기반: `ml/baseline/evaluate.py`, `ml/baseline/train.py`, `ml/advanced/evaluate.py`, `ml/advanced/shap_analysis.py`  
데이터: baseline `data/processed/`, advanced `data/processed/adv_kaggle_only/`  
결과: `reports/adv_kaggle_only/shap_importance.json`

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
# ml/baseline/evaluate.py
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

| 모델 | 알고리즘 | 편향 | 분산 | Test AUC |
|------|----------|------|------|----------|
| RF | Bagging (트리 평균) | 낮음 | **낮음** | 0.7013 |
| XGBoost | Boosting (순차 잔차 학습) | 더 낮음 | 중간 | **0.7641** |
| LightGBM | Boosting (leaf-wise) | 더 낮음 | 중간 | 0.7332 |
| **Ensemble** | Soft Voting (평균) | — | — | **0.7570** |

### 앙상블 방식 (Soft Voting)

```python
# ml/advanced/ensemble.py
def ensemble_predict_proba(models: dict, X: pd.DataFrame) -> np.ndarray:
    rf_p   = models["rf"].predict_proba(X)[:, 1]
    xgb_p  = models["xgb"].predict_proba(X)[:, 1]
    lgbm_p = models["lgbm"].predict_proba(X)[:, 1]
    return (rf_p + xgb_p + lgbm_p) / 3.0
```

### 단일 모델보다 앙상블을 쓰는 이유

XGBoost가 Test AUC 0.7641로 단일 최고 성능이지만 앙상블을 선택한 이유:

1. **오류 독립성**: Bagging(RF)과 Boosting(XGB/LGBM)의 오류 패턴이 다르다.  
   서로 다른 방식으로 틀리기 때문에 평균 시 상쇄된다.
2. **분산 감소**: 단일 Boosting 모델은 하이퍼파라미터에 민감하다. 앙상블로 안정성 확보.
3. **Optuna HPO**: `ml/advanced/optimize.py`에서 Optuna로 각 모델 하이퍼파라미터를 독립 최적화한 후 Soft Voting.

---

## 3. SHAP 도메인 해석

### SHAP 계산 방식

SHAP은 `ml/advanced/shap_analysis.py`에서 TreeExplainer로 RF/XGB/LGBM 각각 산출 후 `reports/adv_kaggle_only/shap_importance.json`으로 저장한다.

```python
# ml/advanced/shap_analysis.py
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_sample)
# summary plot + shap_importance.json 저장
```

### SHAP 일관성

RF·XGBoost·LightGBM의 mean|SHAP| 상위 피처는 거의 같다. 세 모델 모두 `b_prior_games_mean`을 최상위로 두고,
선수의 이전 연도 prior(출전 경험·KD·ADR)를 공통으로 상위에 올린다(`reports/adv_kaggle_only/shap_importance.json`).
서로 다른 알고리즘이 같은 피처군을 중요하게 보므로 피처 중요도 해석의 신뢰성이 높다.

### 도메인 지식과의 일치

실측 mean|SHAP| 상위 피처는 선수의 이전 연도 prior 계열(`prior_games`, `prior_kd`, `prior_adr`)과 synergy다. 이를 Valorant 도메인 지식으로 해석하면:

- **이전 출전 경험 (`prior_games`)**: 누적 출전이 많은 선수일수록 prior 추정이 안정적이며, 팀 전력의 기준점이 된다.
- **이전 교전 성과 (`prior_kd`, `prior_adr`)**: KD(처치/사망 비)와 ADR(라운드당 피해)은 선수의 교전 기여를 요약한다. 이전 시즌 성과가 다음 경기 전력 추정에 반영된다.
- **synergy**: 같은 선수 조합이 이전에 함께 거둔 성과로, 역할 조합뿐 아니라 손발이 맞는 정도를 포착한다.

---

## 4. 데이터 분할 및 피처 계약

### 데이터 경로 및 분할

| 모델 | 데이터 경로 | 분할 방식 | 행 수 (train / test) |
|------|-----------|----------|----------------------|
| ① 랜덤 베이스라인 | `data/processed/` | match_key 랜덤 80/20 | 53,427 / 13,357 |
| ② 랜덤 심화 | `data/processed/adv_kaggle_only/` | match_key 랜덤 80/20 | 53,427 / 13,357 |
| ③ 시간순 베이스라인 | `data/processed/baseline_chrono/` | 연도 블록 ≤2023 / ≥2024 | 53,897 / 12,887 |
| ④ 시간순 심화 | `data/processed/adv_kaggle_chrono/` | 연도 블록 ≤2023 / ≥2024 | 53,897 / 12,887 |

분할별 행 수 차이는 분할 방식에서 비롯한다 — 랜덤 holdout은 전 기간(2021–2026)을 80/20으로, 시간순 holdout은 연도 경계(2024)로 나눈다.

### 피처 수

| 파이프라인 | 피처 수 | 주요 내용 |
|-----------|---------|---------|
| Baseline | **178** | 역할군·스탯·요원 조합·맵 등 |
| Advanced | **125** | 선별 피처 (`data/processed/adv_kaggle_only/` feature contract) |

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

| 모델 | 알고리즘 | 주된 역할 | Test AUC |
|------|----------|-----------|---------|
| **RF** | Bagging (트리 평균) | **분산 감소** — 과적합 내성 | 0.7013 |
| **XGBoost** | Boosting (순차 잔차 학습) | **편향 감소** — 연속형·순서형 피처 처리 강점 | 0.7641 |
| **LightGBM** | Boosting (leaf-wise) | **편향 감소** — 대용량·고차원에서 빠른 학습 | 0.7332 |
| **Ensemble** | Soft Voting | 오류 독립성으로 추가 분산 감소 | **0.7570** |

앙상블의 오류 독립성과 분산 감소 효과는 §2에서 설명된다.

---

## 성과 지표 요약

### Baseline (LR+DT Soft Voting, 178피처)

| 지표 | CV | Test |
|------|----|------|
| ROC-AUC | 0.6599 ± 0.0016 | **0.6587** |
| Accuracy | — | **0.6290** |
| F1 (macro) | — | **0.7231** |

출처: `reports/baseline/metrics.json`

### Advanced (RF+XGB+LGBM Soft Voting, 125피처)

| 지표 | Test (Ensemble) | RF | XGB | LGBM |
|------|----------------|-----|-----|------|
| ROC-AUC | **0.7570** | 0.7013 | 0.7641 | 0.7332 |
| Accuracy | **0.6958** | — | — | — |
| F1 (macro) | **0.7649** | — | — | — |

출처: `reports/adv_kaggle_only/metrics.json`

상세 수치 출처: `ml/advanced/evaluate.py`, `ml/advanced/validate.py`
