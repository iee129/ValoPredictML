# 프로젝트 차별점 검증 — ValoPredictML

기반 코드 (현재 활성 경로):
- 전처리·피처: `ml/baseline/preprocess.py` (baseline 178 / advanced 125 계약 공용), raw 정제 `ml/raw_preprocess.py`
- 학습: baseline `ml/baseline/train.py` (GridSearchCV), advanced `ml/advanced/optimize.py` (Optuna) + `ml/advanced/ensemble.py` (Soft Voting)
- 평가·해석: `ml/baseline/evaluate.py`, `ml/advanced/evaluate.py`, `ml/advanced/shap_analysis.py` (SHAP)
- 검증 코드: `ml/baseline/validate.py`, `ml/advanced/validate.py`

---

## 단순 통계 사이트와 다른 점

| 구분 | 단순 통계 사이트 (tracker.gg 등) | ValoPredictML |
|------|----------------------------------|---------------|
| 예측 단위 | 개별 선수 통계 나열 | 팀 A vs 팀 B **역할 조합 + 이전 연도 prior** |
| 데이터 처리 | 없음 (결과 이후 통계 혼입) | 이전 연도만 prior 집계 + 금지 피처 26개 차단 |
| 검증 방법 | 없음 (단순 표시) | GroupKFold(match_key) 교차검증 |
| 설명 가능성 | 없음 | SHAP TreeExplainer 기여도 |
| 하이퍼파라미터 | 없음 | Optuna TPESampler 자동 최적화 |

---

## 5개 핵심 차별점

### 1. 역할 조합 단위 예측

개별 선수 KDA를 직접 입력하지 않고 **팀 A/B 역할군 카운트 + 요원 카운트**를 피처로 사용한다. advanced 계약은 125피처 (맵 원핫 13, 역할군 카운트 a/b, 29요원 카운트 a/b, 선수 prior, synergy, map×agent, player×agent — 모두 diff 없이 a/b 분리).

```python
# ml/baseline/preprocess.py — _composition_features()
features[f"a_role_{role}_count"] = float(a_count)
features[f"b_role_{role}_count"] = float(b_count)
```

### 2. 이전 연도 prior + 리그 평균 smoothing

선수 통계는 **현재 경기 연도 이전의 이력만** 집계한다(`year < current_year`). 표본이 적은 선수는 해당 prior-window 리그 평균으로 shrink하여 과적합을 막는다. 같은 경기·같은 연도 통계는 구조적으로 제외되므로 prematch 입력만으로 재현 가능하다.

```python
# ml/baseline/preprocess.py — RunningStats.smoothed_avg()
numerator = self.sums.get(stat, 0.0) + PLAYER_PRIOR_SMOOTHING_GAMES * global_avg
denominator = self.games + PLAYER_PRIOR_SMOOTHING_GAMES
# _history_years(): previous_years = [y for y in known_years if y < current_year]
```

### 3. 데이터가 섞이지 않는 분할·검증 (GroupKFold + 금지 피처)

같은 경기(`match_key`)가 train/val/test에 동시에 들어가지 않도록 match_key 단위로 분할하고, baseline CV는 GroupKFold(match_key)로 평가한다. 결과 이후 정보(스코어·라운드·킬·데스·승률 등) 26개 용어는 정규식 패턴으로 차단한다.

```python
# ml/baseline/evaluate.py
gkf = GroupKFold(n_splits=n_splits)
# ml/baseline/preprocess.py — FORBIDDEN_FEATURE_PATTERNS / find_forbidden_feature_names()
```

### 4. SHAP 기반 설명 가능성

`ml/advanced/shap_analysis.py`가 RF/XGB/LGBM 각각에 `shap.TreeExplainer`를 적용해 summary plot 3종과 `reports/adv_kaggle_only/shap_importance.json`(mean|SHAP| 상위 피처)을 산출한다.

```python
# ml/advanced/shap_analysis.py
explainer = shap.TreeExplainer(model)
sv = _positive_class_shap(explainer.shap_values(sample))
```

XGB mean|SHAP| Top5: `b_prior_games_mean`, `a_prior_games_mean`, `a_prior_adr_mean`, `b_prior_adr_mean`, `a_prior_kd_mean` — 선수 이전 출전 경험·성과 prior가 예측에 크게 기여한다(랜덤 holdout 해석 주의는 [`../05_data_learning/03_advanced_models/02_advanced_metric_analysis.md`](../05_data_learning/03_advanced_models/02_advanced_metric_analysis.md) 참조).

### 5. Optuna 하이퍼파라미터 자동 최적화

`ml/advanced/optimize.py`가 rf/xgb/lgbm 각각 TPESampler(seed=42) 50 trial로 GroupKFold ROC-AUC를 최대화한다. study는 sqlite(`reports/adv_kaggle_only/optuna_studies/*.db`)에 저장되고 best params는 `{model}_best_params.json`으로 떨어져 `ensemble.py`가 그대로 소비한다.

```python
# ml/advanced/optimize.py
study = optuna.create_study(
    direction="maximize", load_if_exists=True,
    sampler=optuna.samplers.TPESampler(seed=42),
)
```

CV best value: rf 0.6901, xgb 0.7465, lgbm 0.7139.

---

## 현재 성능 (활성 산출물)

| 구성 | 분할 | Test ROC-AUC | Test Acc | Test F1 |
|------|------|---:|---:|---:|
| 베이스라인 (LR+DT, 178) | 랜덤 holdout | 0.6587 | 0.6290 | 0.7231 |
| 심화 앙상블 (RF+XGB+LGBM, 125) | 랜덤 holdout | 0.7570 | 0.6958 | 0.7649 |
| 베이스라인 (178) | 시간순 holdout | 0.6124 | 0.5795 | 0.6226 |
| 심화 앙상블 (125) | 시간순 holdout | 0.6182 | 0.5885 | 0.6539 |

출처: `reports/{baseline, adv_kaggle_only, baseline_chrono, adv_kaggle_chrono}/metrics.json`. 랜덤 holdout은 전 기간(2021–2026)을 match_key 단위로 무작위 분할(train 53,427 / test 13,357), 시간순 holdout은 2021–2023 학습 / 2024–2026 평가(train 53,897 / test 12,887)다. 4모델 개별·교차 분석: [`./07_model_evaluation/00_overview.md`](./07_model_evaluation/00_overview.md).

---

## 기술 스택 적정성

| 기술 | 사용 여부 | 판정 | 이유 |
|------|-----------|------|------|
| 딥러닝 (Neural Network) | 미사용 | **적절** | 표 형태 데이터 → 트리 기반이 표준 선택 |
| 스택킹 (Stacking Ensemble) | 미사용 (Soft Voting) | **적절** | 단순 평균이 과적합 위험 낮고 해석 용이 |
| SMOTE (클래스 불균형) | 미사용 | **적절** | 레이블 56.8:43.2로 심각한 불균형 없음 |
| Optuna HPO | 사용 (`ml/advanced/optimize.py`) | **적절** | rf/xgb/lgbm 50 trial 자동 최적화 |
| SHAP | 사용 (`ml/advanced/shap_analysis.py`) | **적절** | 트리 모델 기여도 해석 — 강의 가점 항목 |
| 외부 API / 실시간 데이터 | 미사용 | **적절** | 배치 예측 목표; 실시간 필요 없음 |

### 적정 복잡도라는 설계 선택

이 프로젝트의 문제는 **표 형태 이진 분류**다. 이 규모에서 딥러닝은 트리 기반 모델 대비 이점이 없고 해석이 어렵다. 스택킹은 추가 메타 모델로 복잡도만 높이며 단순 평균보다 일관되게 우수하다는 보장이 없다. 트리 앙상블 + Optuna + SHAP은 **문제 규모와 발표 가점 목표에 맞는 적정 복잡도**다.

---

## 사용자 측면 차별점 5개 (2026-05-28 확정)

지도교수 2차 면담(2026-05-25) — "기술 차별점이 아닌 사용자가 체감하는 차별점이 부족하다" — 피드백에 따라 10개 후보를 설계했고, **2026-05-28 검증 회의에서 5개로 축소 확정**. 축소 기준: (a) UI 표시 실현 가능성, (b) 학기 일정 우선순위, (c) 외부 데이터 의존 위험. 위 5개 기술 차별점은 사용자 차별점의 신뢰성 기반이며, 아래 5개는 사용자가 직접 화면에서 체감하는 차별점이다.

시장 분석 근거: [`../competitive_analysis.md`](../competitive_analysis.md) — 4가지 빈자리.
데이터원 매핑: [`../07_data/02_primary_datasets/04_vlrgg.md`](../07_data/02_primary_datasets/04_vlrgg.md).

### 차별점 인벤토리 (확정 5개)

| 그룹 | # | 차별점 | 산출 파일 | 동력 | VLR.gg | 데이터원 |
|------|---|--------|-----------|------|--------|----------|
| 1. 입력 즉시 피드백 | N | 맵 메타 적합도 | `ml/differentiators/agent_map_fit.py` **(미구현 예정)**, `data/research/agent_map_fit.json` | 룰 | ✗ | `docs/10_valorant/agents.md` |
| 1 | K | 메타 조합 매칭률 | `ml/differentiators/map_ideal_comp.py` **(미구현 예정)**, `data/research/map_ideal_comp.json` | 룰 | ✗ | `docs/10_valorant/maps.md` |
| 1 | G | 조합 밸런스 경고 | `ml/differentiators/risk_alert.py` **(미구현 예정)** | 룰 (5개 코드 내장) | ✗ | 도메인 룰 |
| 1 | D | 주력 요원 이탈 알림 (30/60/90일) | `ml/differentiators/player_agent_pool.py` **(미구현 예정)** | 외부 API + 룰 | ✓ | `vlrggapi /player/{id}` + 자체 CSV fallback |
| 2. 예측 결과 해석 | C | 승부 근거 카드 (자연어 설명) | `ml/differentiators/nl_explain.py` **(미구현 예정)** | 모델 SHAP + 한국어 템플릿 | ✗ | SHAP + 사전 정의 템플릿 |

> 위 `ml/differentiators/*`는 사용자 차별점 구현 예정 경로이며 현재 미구현 (디렉토리 미존재). 차별점 C는 본 문서 §4의 SHAP 산출(`ml/advanced/shap_analysis.py`)을 한국어 템플릿으로 변환한다.

### 제외된 5개 (참고)

| # | 차별점 | 제외 사유 |
|---|--------|-----------|
| I | 카운터 픽 경고 | 라운드 단위 능력 상호작용 데이터 부재 (`research_validation.json: counter-pair facts 0 rows`). 룰 코드화는 가능하나 모델·데이터 기반 정당성 약함 |
| B | 박빙 경기 검증 (Brier·ECE) | 학술적 가치는 있으나 학기 발표에서 청중 이해도 낮음. 차기 평가 단계로 이월 |
| J | Ult Cycle Balance | 데이터로 검증된 가치 약함. 도메인 룰만으로 차별점 의미 한정 |
| A | What-if 시뮬레이션 | Streamlit session_state 구현 복잡도 + 학기 일정. 차기 작업으로 이월 (`app/whatif.py` — 미구현, 경로 미결정) |
| E | 공·수 사이드 (ATK/DEF) 패널 | VLR.gg team stats 스크래핑 안정성 위험. 차기 작업으로 이월 |

### 사용자 차별점의 단위 테스트 (5개)

`tests/differentiators/` 하위 5개 파일로 차별점마다 acceptance 검증:

| 테스트 파일 | 검증 |
|-------------|------|
| `test_agent_map_fit.py` | 29 요원 × 13 맵 ≥80% 채워짐, 핵심 페어 정확 |
| `test_map_ideal_comp.py` | 12 맵 등록, 매칭률·누락 역할군 정확 |
| `test_risk_alert.py` | 5개 룰 작동, 위배 0건 시 빈 list |
| `test_player_agent_pool.py` | mock vlrggapi 응답 → out-of-pool 검출, CSV fallback 작동 |
| `test_nl_explain.py` | SHAP 합산 vs 예측 확률 오차 ≤0.01, 템플릿 fallback |

통합 테스트: `tests/integration/test_streamlit_integration.py` — 5개 차별점 동시 렌더링 + VLR.gg 실패 시 fallback 작동.

### 시장 빈자리 4개 대응 (3개 대응 / 1개 이월)

| 빈자리 (competitive_analysis.md 결론 7.1) | 본 프로젝트 응답 |
|-------------------------------------------|-------------------|
| 1. prematch 모델 기반 승률 예측 | Baseline(0.6587, 완료) + 심화 앙상블(0.7570, 완료) + VLR.gg 통합(예정) |
| 2. What-if 시뮬레이션 | 학기 일정 외 — 차기 작업으로 이월 |
| 3. 자연어 예측 근거 | **C** |
| 4. 개인화 (선수 풀·약점 기반) | **D** ★ 정면 대응 + **G·N·K** 도메인 보조 |
