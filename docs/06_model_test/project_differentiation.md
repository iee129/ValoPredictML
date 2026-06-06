# 프로젝트 차별점 검증 — ValoPredictML

기반 코드 (현재 활성 경로):
- 전처리·피처: `src/features/preprocess.py` (baseline 421 / advanced 179 계약 공용), raw 정제 `src/data/raw_preprocess.py`
- 학습: baseline `src/ml/baseline/train.py`, advanced `src/ml/advanced/ensemble.py` (Soft Voting)
- 평가·해석: `src/ml/baseline/evaluate.py`, `src/ml/advanced/evaluate.py`, `src/ml/advanced/feature_importance.py` (`feature_importances_`)
- 검증 코드: `src/ml/baseline/validate.py`, `src/ml/advanced/validate.py`

본 프로젝트는 베이스라인 1개(LR+DT, 랜덤 80/20, 421피처) + 심화 1개(RF+XGB+LGBM, 시간순 holdout, 179피처) 2개 모델을 비교한다.

---

## 단순 통계 사이트와 다른 점

| 구분 | 단순 통계 사이트 (tracker.gg 등) | ValoPredictML |
|------|----------------------------------|---------------|
| 예측 단위 | 개별 선수 통계 나열 | 팀 A vs 팀 B **역할 조합 + 이전 연도 prior** |
| 데이터 처리 | 없음 (결과 이후 통계 혼입) | 이전 연도만 prior 집계 + 금지 피처 26개 차단 |
| 검증 방법 | 없음 (단순 표시) | GroupKFold(match_key) 교차검증 + 시간순 holdout |
| 설명 가능성 | 없음 | 트리 `feature_importances_` 기반 기여도 + 한국어 자연어 근거 |
| 하이퍼파라미터 | 없음 | 트리 앙상블 가중 soft voting (2.0:3.0:0.1) |

---

## 5개 핵심 차별점

### 1. 역할 조합 단위 예측

개별 선수 KDA를 직접 입력하지 않고 **팀 A/B 역할군 카운트 + 요원 카운트**를 피처로 사용한다. advanced 계약은 179피처 (Drift 제외 맵 원핫 12, 역할군 count a/b, 주요 요원 count a/b + other, 선수 prior·synergy·map×agent·player×agent a/b/diff, cold-start flag, team form).

```python
# src/features/preprocess.py — _composition_features()
features[f"a_role_{role}_count"] = float(a_count)
features[f"b_role_{role}_count"] = float(b_count)
```

### 2. 이전 연도 prior + 리그 평균 smoothing

선수 통계는 **현재 경기 연도 이전의 이력만** 집계한다(`year < current_year`). 표본이 적은 선수는 해당 prior-window 리그 평균으로 shrink하여 과적합을 막는다. 같은 경기·같은 연도 통계는 구조적으로 제외되므로 prematch 입력만으로 재현 가능하다.

```python
# src/features/preprocess.py — RunningStats.smoothed_avg()
numerator = self.sums.get(stat, 0.0) + PLAYER_PRIOR_SMOOTHING_GAMES * global_avg
denominator = self.games + PLAYER_PRIOR_SMOOTHING_GAMES
# _history_years(): previous_years = [y for y in known_years if y < current_year]
```

### 3. 데이터가 섞이지 않는 분할·검증 (GroupKFold + 금지 피처)

같은 경기(`match_key`)가 train/val/test에 동시에 들어가지 않도록 match_key 단위로 분할하고, baseline CV는 GroupKFold(match_key)로 평가한다. 결과 이후 정보(스코어·라운드·킬·데스·승률 등) 26개 용어는 정규식 패턴으로 차단한다.

```python
# src/ml/baseline/evaluate.py
gkf = GroupKFold(n_splits=n_splits)
# src/features/preprocess.py — FORBIDDEN_FEATURE_PATTERNS / find_forbidden_feature_names()
```

### 4. 피처 중요도 기반 설명 가능성

`src/ml/advanced/feature_importance.py`가 RF/XGB/LGBM의 트리 `feature_importances_`로 상위 피처를 산출하고, 직렬화 단계(`serializers.py`)에서 `importance × value` 휴리스틱으로 한국어 자연어 근거를 생성한다(진짜 SHAP 값은 아니다).

상위 중요도 피처는 `prior_games`, `prior_kd`, `prior_adr` 계열 — 선수 이전 출전 경험·성과 prior가 예측에 크게 기여한다(분할별 해석 주의는 [`../05_data_learning/03_advanced_models/02_advanced_metric_analysis.md`](../05_data_learning/03_advanced_models/02_advanced_metric_analysis.md) 참조).

### 5. 트리 앙상블 가중 soft voting

`src/ml/advanced/ensemble.py`가 RF·XGBoost·LightGBM의 확률을 가중치 2.0:3.0:0.1로 결합하는 soft voting 앙상블을 구성한다. Optuna 같은 자동 하이퍼파라미터 탐색은 사용하지 않고, 각 모델은 코드에 고정된 하이퍼파라미터로 학습한다.

세 트리 모델의 시간순 Test AUC는 RF 0.6965 / XGB 0.7007 / LGBM 0.7015로 근접하며, 가중 앙상블이 0.7010으로 안정적으로 수렴한다.

---

## 현재 성능 (활성 산출물)

| 구성 | 분할 | Test ROC-AUC | Test Acc | Test F1 |
|------|------|---:|---:|---:|
| 베이스라인 (LR+DT, 421) | 랜덤 80/20 | 0.5943 | 0.5667 | 0.6072 |
| 심화 앙상블 (RF+XGB+LGBM, 179) | 시간순 (train 2020–2025 / test 2026, 맵 단위 승패 샘플) | 0.7010 | 0.6454 | 0.6478 |

출처: 베이스라인 발표자료(PDF) 보고값, 심화 `reports/advanced/metrics.json`. 두 모델은 분할·모델 축이 모두 다르므로 두 수치는 같은 잣대의 우열이 아니다. 개별·비교 분석: [`./07_model_evaluation/00_overview.md`](./07_model_evaluation/00_overview.md).

---

## 기술 스택 적정성

| 기술 | 사용 여부 | 판정 | 이유 |
|------|-----------|------|------|
| 딥러닝 (Neural Network) | 미사용 | **적절** | 표 형태 데이터 → 트리 기반이 표준 선택 |
| 스택킹 (Stacking Ensemble) | 미사용 (Soft Voting) | **적절** | 단순 평균이 과적합 위험 낮고 해석 용이 |
| SMOTE (클래스 불균형) | 미사용 | **적절** | 레이블 56.8:43.2로 심각한 불균형 없음 |
| Optuna HPO | 미사용 (고정 하이퍼파라미터) | **적절** | 트리 가중 soft voting로 충분; 자동 탐색 없이 안정적 |
| 피처 중요도 | 사용 (`src/ml/advanced/feature_importance.py`, `feature_importances_`) | **적절** | 트리 모델 기여도 해석 — 강의 가점 항목 (진짜 SHAP은 아님) |
| 외부 API / 실시간 데이터 | 미사용 | **적절** | 배치 예측 목표; 실시간 필요 없음 |

### 적정 복잡도라는 설계 선택

이 프로젝트의 문제는 **표 형태 이진 분류**다. 이 규모에서 딥러닝은 트리 기반 모델 대비 이점이 없고 해석이 어렵다. 스택킹은 추가 메타 모델로 복잡도만 높이며 단순 평균보다 일관되게 우수하다는 보장이 없다. 트리 앙상블(가중 soft voting) + 피처 중요도 해석은 **문제 규모와 발표 가점 목표에 맞는 적정 복잡도**다.

---

## 사용자 측면 차별점 5개 (2026-05-28 확정)

지도교수 2차 면담(2026-05-25) — "기술 차별점이 아닌 사용자가 체감하는 차별점이 부족하다" — 피드백에 따라 10개 후보를 설계했고, **2026-05-28 검증 회의에서 5개로 축소 확정**. 축소 기준: (a) UI 표시 실현 가능성, (b) 학기 일정 우선순위, (c) 외부 데이터 의존 위험. 위 5개 기술 차별점은 사용자 차별점의 신뢰성 기반이며, 아래 5개는 사용자가 직접 화면에서 체감하는 차별점이다.

시장 분석 근거: [`../competitive_analysis.md`](../competitive_analysis.md) — 4가지 빈자리.
데이터원 매핑: [`../07_data/02_primary_datasets/04_vlrgg.md`](../07_data/02_primary_datasets/04_vlrgg.md).

### 차별점 인벤토리 (확정 5개)

| 그룹 | # | 차별점 | 산출 파일 | 동력 | VLR.gg | 데이터원 |
|------|---|--------|-----------|------|--------|----------|
| 1. 입력 즉시 피드백 | N | 맵 메타 적합도 | `ml/differentiators/agent_map_fit.py` **(미구현 예정)**, `data/research/agent_map_fit.json` | 룰 | ✗ | `docs/09_valorant/agents.md` |
| 1 | K | 메타 조합 매칭률 | `ml/differentiators/map_ideal_comp.py` **(미구현 예정)**, `data/research/map_ideal_comp.json` | 룰 | ✗ | `docs/09_valorant/maps.md` |
| 1 | G | 조합 밸런스 경고 | `ml/differentiators/risk_alert.py` **(미구현 예정)** | 룰 (5개 코드 내장) | ✗ | 도메인 룰 |
| 1 | D | 주력 요원 이탈 알림 (30/60/90일) | `ml/differentiators/player_agent_pool.py` **(미구현 예정)** | 외부 API + 룰 | ✓ | `vlrggapi /player/{id}` + 자체 CSV fallback |
| 2. 예측 결과 해석 | C | 승부 근거 카드 (자연어 설명) | `ml/differentiators/nl_explain.py` **(미구현 예정)** | 모델 SHAP + 한국어 템플릿 | ✗ | SHAP + 사전 정의 템플릿 |

> 위 `ml/differentiators/*`는 사용자 차별점 구현 예정 경로이며 현재 미구현 (디렉토리 미존재). 차별점 C는 본 문서 §4의 피처 중요도 산출(`src/ml/advanced/feature_importance.py`)을 한국어 템플릿으로 변환한다.

### 제외된 5개 (참고)

| # | 차별점 | 제외 사유 |
|---|--------|-----------|
| I | 카운터 픽 경고 | 라운드 단위 능력 상호작용 데이터 부재 (`research_validation.json: counter-pair facts 0 rows`). 룰 코드화는 가능하나 모델·데이터 기반 정당성 약함 |
| B | 박빙 경기 검증 (Brier·ECE) | 학술적 가치는 있으나 학기 발표에서 청중 이해도 낮음. 차기 평가 단계로 이월 |
| J | Ult Cycle Balance | 데이터로 검증된 가치 약함. 도메인 룰만으로 차별점 의미 한정 |
| A | What-if 시뮬레이션 | 프런트 상태 관리 구현 복잡도 + 학기 일정. 차기 작업으로 이월 (미구현, 경로 미결정) |
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

통합 테스트: `tests/integration/test_web_integration.py` — 5개 차별점 동시 렌더링 + VLR.gg 실패 시 fallback 작동.

### 시장 빈자리 4개 대응 (3개 대응 / 1개 이월)

| 빈자리 (competitive_analysis.md 결론 7.1) | 본 프로젝트 응답 |
|-------------------------------------------|-------------------|
| 1. prematch 모델 기반 승률 예측 | Baseline(랜덤 80/20, 0.5943, 완료) + 심화 앙상블(시간순, 0.7010, 완료) + VLR.gg 통합(예정) |
| 2. What-if 시뮬레이션 | 학기 일정 외 — 차기 작업으로 이월 |
| 3. 자연어 예측 근거 | **C** |
| 4. 개인화 (선수 풀·약점 기반) | **D** ★ 정면 대응 + **G·N·K** 도메인 보조 |
