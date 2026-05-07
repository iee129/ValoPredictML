# 검증 결과 종합 요약 — ValoPredictML

기반: `reports/eval_summary.json`, `reports/baseline_comparison.json`,  
`reports/generalization_check.json`, `reports/shap_analysis.json`

---

## 1. 성과지표 스냅샷 (eval_summary.json)

### K-Fold 교차검증 결과

| 모델 | Accuracy | F1 (macro) | ROC-AUC |
|------|----------|-----------|---------|
| RF | 0.8652 ± 0.0017 | 0.8652 ± 0.0017 | 0.9449 ± 0.0012 |
| XGBoost | 0.8488 ± 0.0028 | 0.8488 ± 0.0028 | 0.9343 ± 0.0019 |
| LightGBM | 0.8494 ± 0.0027 | 0.8494 ± 0.0027 | 0.9353 ± 0.0019 |
| **Ensemble** | **0.8580 ± 0.0034** | **0.8580 ± 0.0034** | **0.9414 ± 0.0017** |

### Test 세트 최종 평가

| 모델 | Accuracy | F1 (macro) | ROC-AUC |
|------|----------|-----------|---------|
| RF | 0.8595 | 0.8566 | 0.9378 |
| XGBoost | 0.8443 | 0.8408 | 0.9281 |
| LightGBM | 0.8480 | 0.8447 | 0.9292 |
| **Ensemble** | **0.8540** | **0.8508** | **0.9355** |

---

## 2. Baseline 비교 (baseline_comparison.json)

| 기준선 | Accuracy |
|--------|----------|
| 무작위 (Random) | 0.5000 |
| 다수 클래스 (Majority, label=1) | 0.5687 |
| **Ensemble (Test)** | **0.8540** |

**개선폭: +29.13%p** (다수 클래스 기준 대비)

---

## 3. 과적합 판정 (generalization_check.json)

| 항목 | 값 |
|------|-----|
| K-Fold Accuracy (평균) | 0.8580 |
| Test Accuracy | 0.8540 |
| **Gap** | **0.004** |
| 기준 (과적합 경계) | 0.03 |
| `overfitting_flag` | **false** |
| 판정 | **PASS — 과적합 없음** |

gap=0.004로 K-Fold와 test 간 성능이 일관적이다.

---

## 4. SHAP 일관성 (shap_analysis.json)

### 모델 간 Spearman 상관관계

| 비교 | Spearman r | 판정 |
|------|-----------|------|
| RF vs XGBoost | **0.899** | 높음 (> 0.7) |
| RF vs LightGBM | 0.898 | 높음 |
| XGBoost vs LightGBM | 0.992 | 거의 동일 |

`consistency_verdict: "높음 (r=0.899 > 0.7)"`

### Top 5 피처 (XGBoost 기준)

| 순위 | 피처 | SHAP 값 | 해석 |
|------|------|---------|------|
| 1 | `a_avg_assists` | 1.107 | 팀 A 어시스트 — 협력 전투력 |
| 2 | `b_avg_assists` | 1.051 | 팀 B 어시스트 — 협력 전투력 |
| 3 | `b_fk_fd_ratio` | 0.630 | 팀 B 선빵/선죽 비율 |
| 4 | `a_fk_fd_ratio` | 0.520 | 팀 A 선빵/선죽 비율 |
| 5 | `b_avg_agent_exp` | 0.340 | 팀 B 요원 숙련도 |

세 모델이 일관되게 **어시스트**와 **FK/FD ratio**를 가장 중요한 피처로 식별한다.  
이는 Valorant 도메인 지식(팀 플레이·선제 교전 우위)과 일치한다.

---

## 5. 검증 통과 체크리스트

| 검증 항목 | 기준 | 결과 | 상태 |
|-----------|------|------|------|
| Baseline 대비 개선 | > +10%p | +29.13%p | ✓ PASS |
| 과적합 여부 | gap < 0.03 | gap = 0.004 | ✓ PASS |
| SHAP 일관성 | r > 0.7 | r = 0.899 | ✓ PASS |
| ROC-AUC (Ensemble Test) | > 0.9 | 0.9355 | ✓ PASS |
| F1 (Ensemble Test) | > 0.8 | 0.8508 | ✓ PASS |
| Accuracy (Ensemble Test) | > 0.8 | 0.8540 | ✓ PASS |

---

## 결론

**이 프로젝트는 ML 개념적으로 올바르다.**

근거:

1. **실질적 예측력**: 다수 클래스 baseline 대비 +29.13%p 개선 — 모델이 의미 있는 패턴을 학습했다.
2. **일반화 검증**: K-Fold vs Test gap=0.004로 과적합이 없다. GroupKFold(match_key 단위)가 실제 배포 환경을 정직하게 시뮬레이션했다.
3. **피처 신뢰성**: 세 독립 모델의 SHAP 순위가 r=0.899로 일치한다 — 특정 모델의 아티팩트가 아닌 실제 신호다.
4. **도메인 정합성**: 최상위 피처(어시스트, FK/FD ratio, 요원 숙련도)가 Valorant 게임 메카닉과 일치한다.
5. **검증 프로세스 무결성**: leakage-free GroupKFold, holdout test, 독립 SHAP 검증으로 다층 검증 완료.
