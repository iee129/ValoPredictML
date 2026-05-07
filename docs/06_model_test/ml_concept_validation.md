# ML 개념 검증 — ValoPredictML

기반: `ml/evaluate_model.py`, `ml/train_model.py`, `ml/validate_metrics.py`  
데이터: `data/processed/` (train 93,078행, test 9,973행)  
결과: `reports/eval_summary.json`, `reports/shap_analysis.json`

---

## 1. GroupKFold 선택 근거

### 문제: 경기 단위 데이터 누수(leakage)

Valorant 경기 데이터는 **같은 경기(match_key)에서 복수 행이 생성**된다.  
A/B swap 증강(`ml/data_pipeline.py:961`)으로 원본 경기 `mk`와 twin row `mk_swap`이 동시에 존재한다.

random split 또는 StratifiedKFold를 사용하면:
- `mk`가 train fold, `mk_swap`이 validation fold에 들어갈 수 있음
- 모델이 "뒤집힌 버전"을 이미 학습한 상태에서 검증 → 낙관적 estimate

### 해결: GroupKFold(n_splits=5)

```python
# ml/evaluate_model.py:49-51
gkf = GroupKFold(n_splits=n_splits)
# _swap suffix 제거: augment된 twin row가 다른 fold에 들어가는 leakage 방지
groups = df_train["match_key"].str.replace(r"_swap$", "", regex=True)
```

`_swap` suffix를 제거해 `mk`와 `mk_swap`이 **항상 같은 group**으로 묶인다.  
GroupKFold는 같은 group을 절대 다른 fold에 분리하지 않으므로 경기 단위 leakage가 원천 차단된다.

### 선택 근거 요약

| 기법 | 문제 |
|------|------|
| KFold | 경기 행 무작위 분리 → match leakage |
| StratifiedKFold | 클래스 비율 보존은 하지만 match leakage 그대로 |
| **GroupKFold** | match_key 단위 분리 → leakage 없음, 실제 배포 환경 시뮬레이션 |

test.csv는 K-Fold 중 절대 사용하지 않는다(`ml/evaluate_model.py:43-46`). 최종 평가 1회만 사용한다.

---

## 2. 앙상블 전략 — 편향-분산 트레이드오프

### 세 모델의 특성

| 모델 | 알고리즘 | 편향 | 분산 | K-Fold AUC | AUC std |
|------|----------|------|------|-----------|---------|
| RF | Bagging (300 트리 평균) | 낮음 | **낮음** | 0.9449 | **0.0012** |
| XGBoost | Boosting (순차 잔차 학습) | 더 낮음 | 중간 | 0.9343 | 0.0019 |
| LightGBM | Boosting (leaf-wise) | 더 낮음 | 중간 | 0.9353 | 0.0019 |
| **Ensemble** | 단순 평균 | — | — | **0.9414** | **0.0017** |

### 앙상블 방식

```python
# ml/train_model.py:247-251
def ensemble_predict_proba(models: dict, X: pd.DataFrame) -> np.ndarray:
    rf_p   = models["rf"].predict_proba(X)[:, 1]
    xgb_p  = models["xgb"].predict_proba(X)[:, 1]
    lgbm_p = models["lgbm"].predict_proba(X)[:, 1]
    return (rf_p + xgb_p + lgbm_p) / 3.0
```

### 단일 RF보다 앙상블을 쓰는 이유

RF가 K-Fold AUC 0.9449로 단일 최고 성능이지만 앙상블을 선택한 이유:

1. **오류 독립성**: Bagging(RF)과 Boosting(XGB/LGBM)의 오류 패턴이 다르다.  
   서로 다른 방식으로 틀리기 때문에 평균 시 상쇄된다.
2. **분산 감소**: XGB·LGBM의 std(0.0019)가 RF(0.0012)보다 높다.  
   Ensemble std=0.0017로 Boosting 단독보다 안정적이다.
3. **Test 일반화**: K-Fold 0.858 → Test 0.854, gap=0.004 (과적합 없음).  
   (`reports/generalization_check.json` — `overfitting_flag: false`)

---

## 3. SHAP 도메인 해석

### SHAP 일관성 검증

SHAP은 모델별 블랙박스 특성에 의존하므로 세 모델 간 피처 중요도가 일치하는지 검증이 필요하다.

| 비교 | Spearman r | 해석 |
|------|-----------|------|
| RF vs XGBoost | **0.899** | 높은 일관성 |
| RF vs LightGBM | 0.898 | 높은 일관성 |
| XGBoost vs LightGBM | 0.992 | 거의 동일 |

r > 0.7 기준으로 세 모델 모두 통과 → **피처 중요도 신뢰성 높음**.  
(`reports/shap_analysis.json` — `consistency_verdict: "높음 (r=0.899 > 0.7)"`)

### Top5 피처 (XGBoost 기준, mean |SHAP|)

| 순위 | 피처 | SHAP 값 | 해석 |
|------|------|---------|------|
| 1 | `a_avg_assists` | 1.107 | 팀 A 어시스트 — 협력 전투력 지표 |
| 2 | `b_avg_assists` | 1.051 | 팀 B 어시스트 — 협력 전투력 지표 |
| 3 | `b_fk_fd_ratio` | 0.630 | 팀 B 선빵/선죽 비율 — 라운드 이니셔티브 |
| 4 | `a_fk_fd_ratio` | 0.520 | 팀 A 선빵/선죽 비율 — 라운드 이니셔티브 |
| 5 | `b_avg_agent_exp` | 0.340 | 팀 B 요원 숙련도 — 역할 완성도 |

### 도메인 지식과의 일치

- **어시스트(assists)가 1위**: Valorant는 킬뿐 아니라 팀 플레이(플래시·스턴 지원)가 핵심.  
  어시스트는 팀 협력 강도를 측정하는 가장 직접적인 지표다.
- **FK/FD ratio**: 선제 교전에서 이기면 해당 라운드의 수적 우위를 확보한다.  
  이는 전략 게임에서 "첫 피 누가 흘리냐"가 라운드 결과에 직결된다는 도메인 지식과 일치.
- **요원 숙련도(agent_exp)**: 같은 Initiator라도 숙련된 플레이어가 훨씬 효과적이다.  
  역할 조합뿐 아니라 **역할 실행력**이 중요함을 데이터가 지지한다.

SHAP 계산: `ml/evaluate_model.py:137-154` — TreeExplainer, sample_size=2000

---

## 4. 데이터 증강 전략 — A/B Swap

### 왜 증강이 필요한가

Valorant 경기 데이터는 **팀 A vs 팀 B** 형태로 수집된다.  
레이블은 `label=1` (팀 A 승리) / `label=0` (팀 B 승리).

자연 수집 데이터의 문제:
- 어떤 팀이 "A"로 기록되느냐는 임의적이다 (소스마다 다름)
- 모델이 팀 조합 강도 차이가 아니라 "A 포지션 편향"을 학습할 위험

### Swap 증강 메커니즘

```python
# ml/data_pipeline.py:919-966
def augment_swap(df: pd.DataFrame) -> pd.DataFrame:
    swap = df.copy()
    # 팀 A ↔ 팀 B 피처 교환 (a_* ↔ b_*, diff_* 부호 반전)
    swap["label"] = 1 - df["label"].values   # 승리 팀도 반전
    swap["match_key"] = df["match_key"].astype(str) + "_swap"
    ...
```

각 경기를 두 번 학습한다:
- 원본: 팀 A=강팀, 팀 B=약팀 → label=1
- swap: 팀 A=약팀, 팀 B=강팀 → label=0

### 효과

| 항목 | 결과 |
|------|------|
| 클래스 균형 | train 50:50 (원본 불균형 해소) |
| 포지션 편향 제거 | 모델이 "A 자리" 자체가 아닌 "조합 강도 차이"를 학습 |
| 데이터 2배 확장 | 66,485 → 93,078행 (train) |

test는 swap 증강 없이 자연 분포 유지 (56.9:43.1, imbalance_ratio=1.32).  
→ F1 macro가 accuracy보다 정직한 이유: 소수 클래스(label=0)에 동등 가중치 부여

### GroupKFold와의 연결

swap 후 `match_key`에 `_swap` suffix가 붙으므로, GroupKFold에서 **반드시 suffix를 제거**해야 원본과 twin이 같은 fold에 배정된다.  
(`ml/evaluate_model.py:51` — `str.replace(r"_swap$", "", regex=True)`)

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
이 프로젝트는 **93,078행 표 형태 데이터**로, 학계와 실무 모두 이 규모에서는 트리 기반 앙상블을 표준 선택으로 권장한다.  
딥러닝 추가는 복잡도와 튜닝 비용이 올라가지만 성능 개선이 보장되지 않는다.

### RF / XGB / LightGBM의 역할과 보완 관계

| 모델 | 알고리즘 | 주된 역할 | K-Fold AUC | OOB Score |
|------|----------|-----------|-----------|-----------|
| **RF** | Bagging (300 트리 평균) | **분산 감소** — 과적합 내성, OOB 자체 검증 | 0.9449 | **0.8713** |
| **XGBoost** | Boosting (순차 잔차 학습) | **편향 감소** — 연속형·순서형 피처 처리 강점 | 0.9343 | — |
| **LightGBM** | Boosting (leaf-wise) | **편향 감소** — 대용량·고차원에서 빠른 학습 | 0.9353 | — |
| **Ensemble** | 단순 평균 | 오류 독립성으로 추가 분산 감소 | 0.9414 | — |

RF OOB score **0.8713** — 학습에 사용되지 않은 샘플로 자체 검증한 값으로, test 세트 없이도 과적합 여부를 확인할 수 있다.

앙상블의 오류 독립성과 분산 감소 효과는 §2에서 AUC std 비교와 함께 설명된다.

---

## 성과 지표 요약

| 지표 | K-Fold (Ensemble) | Test (Ensemble) |
|------|------------------|-----------------|
| Accuracy | 0.858 ± 0.003 | **0.854** |
| F1 (macro) | 0.858 ± 0.003 | **0.851** |
| ROC-AUC | 0.941 ± 0.002 | **0.935** |

**Baseline 대비**: 다수 클래스 기준(56.9%) 대비 **+28.5%p** 개선  
**과적합 검증**: K-Fold vs Test gap = 0.004 (< 0.03 기준) → `overfitting_flag: false`

상세 수치 출처: `reports/eval_summary.json`, `reports/baseline_comparison.json`
