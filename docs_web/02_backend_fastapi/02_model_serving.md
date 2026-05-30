# 02. 모델 서빙 (app/predict.py 재사용)

## 1. 재사용하는 함수 (재구현 금지)

FastAPI는 아래 `app/predict.py` 공개 함수만 호출한다. 시그니처는 실제 코드 그대로다.

| 함수 | 시그니처 | 용도 |
|------|----------|------|
| `predict_custom_lineup` | `(map_name, cutoff_year, team_a_slots, team_b_slots) -> PredictionResult` | `POST /predict` |
| `predict_replay_match` | `(match_key) -> PredictionResult` | `GET /replay/{match_key}` |
| `available_options` | `() -> dict` | `/options`, `/agents`, `/maps`, `/players`, `/years` |
| `load_model` | `() -> (model, meta)` | `/model`, `/health`, 워밍업 |
| `load_reports` | `() -> {metrics, validation}` | `/model` |
| `global_feature_importance` | `(limit=20) -> list[{feature, importance}]` | `/model` |

`team_a_slots` / `team_b_slots` 형식: `list[dict[str, str]]`, 각 원소 `{"player": "<선수명>", "agent": "<요원명>"}`, 길이 5.

---

## 2. `predict_custom_lineup` 내부 동작 (콜드스타트 원인)

```
predict_custom_lineup(map, cutoff_year, team_a_slots, team_b_slots)
  └─ _custom_feature_frame(...)
       ├─ _validate_slots(...)              # 5×2 슬롯, 선수 10명 유일, 팀내 요원 유일
       ├─ normalize_map(map)                # 13맵 화이트리스트
       ├─ _slot_to_player_input(slot)       # player_key, agent_key, role 정규화
       ├─ _history_state_before_year(processed_dir, cutoff_year)   # ★ 무거움 (lru_cache=8)
       │     └─ _historical_match_inputs(processed_dir)            # ★ matches/players 전체 로드 (lru_cache=2)
       └─ _build_feature_row(..., agent_keys=MODELED_AGENT_KEYS_ADVANCED, include_diff=False)
            → 125피처 1행
  └─ _result_from_features(X)               # ensemble.predict_proba(X)[:,1]
```

- **첫 호출**: `_historical_match_inputs`가 `data/processed/{matches,players}.csv` 전체를 읽어 이전연도 누적 상태를 만든다. 데이터 규모상 수 초~수십 초.
- **이후 호출**: `lru_cache`로 즉시 반환. `cutoff_year`별로 캐시(maxsize=8).
- **시연 대응**: `lifespan` startup에서 `predict_custom_lineup`을 더미 라인업으로 1회 호출하거나, 최소한 `available_options()` + `load_model()`을 워밍업하라. replay 경로는 콜드스타트가 없다.

---

## 3. `PredictionResult` 필드 (출력 원본)

`app/predict.py`의 `@dataclass PredictionResult`. 응답 직렬화의 단일 출처다.

| 필드 | 타입 | 비고 |
|------|------|------|
| `team_a_win_probability` | float | 팀 A 승률 (0~1) |
| `team_b_win_probability` | float | = 1 - team_a |
| `confidence` | float | `abs(prob_a - 0.5) * 2` |
| `predicted_label` | int | `1` if prob_a ≥ 0.5 else `0` (1=팀 A 승 예측) |
| `top_features` | list[dict] | `{feature, value, importance, contribution}` ×8 |
| `role_counts` | dict | `{"A팀": {역할라벨: n}, "B팀": {...}}` (한국어 역할 라벨) |
| `model_metadata` | dict | `meta.json` 전체 |
| `report_metadata` | dict | `{metrics, validation}` |
| `match_key` | str\|None | replay만 채워짐 |
| `map_name` | str\|None | 정규화된 맵 |
| `team_a` / `team_b` | str | 커스텀은 "A팀"/"B팀", replay는 실제 팀명 |
| `actual_label` | int\|None | replay만 (실제 승팀) |
| `source` | str\|None | replay만 |
| `feature_values` | dict\|None | 125피처 전체 값 (디버그/심화 표시용) |

> `role_counts` 키는 `role_label()`로 한국어("타격대/척후대/전략가/감시자")다. API 응답에서는 **canonical 키(duelist/initiator/controller/sentinel)로 정규화**해 내보내는 것을 권장한다(직렬화 규칙 → [04_schemas.md](04_schemas.md)).

---

## 4. `top_features[].feature`는 실제 피처명이다

09_web은 `"팀 조합 다양성"` 같은 **존재하지 않는 라벨**을 넣었다. 실제 `feature`는 `FEATURE_COLS_ADVANCED`의 컬럼명이다. 예:

| feature (원본 컬럼) | 의미 (`feature_label()` 변환) |
|----------------------|-------------------------------|
| `a_prior_kd_mean` | A팀 이전 연도 선수 평균 K/D |
| `b_player_agent_adr_mean` | B팀 선수-요원 이전 평균 평균 피해량 |
| `a_role_duelist_count` | A팀 타격대 수 |
| `map_ascent` | 맵: 어센트 |
| `a_synergy_mean` | A팀 선수 동료 경험 평균 |

프론트는 `feature` 원본 키를 받고, 한국어 라벨이 필요하면 `app/predict.py`의 `feature_label()`과 동일한 매핑을 자체 보유하거나, 백엔드가 `label` 필드를 추가로 직렬화한다(권장). → [04_schemas.md](04_schemas.md) §3.

---

## 5. 모델 메타·지표 (`/model`)

- `load_model()[1]` = `models/advanced/meta.json`: `algorithm="RF+XGB+LGBM_soft_voting"`, `n_features=125`, `feature_contract="advanced"`, `feature_names`, `validation.final_verdict` 등.
- `load_reports()`:
  - `metrics` = `reports/adv_kaggle_only/metrics.json` → `test_auc`, `test_acc`, F1 등.
  - `validation` = `.../validation.json` → `final_verdict="PASS_TRUSTED_KAGGLE_ONLY_ADVANCED"`, 게이트 결과.
- `global_feature_importance(limit)` → 앙상블 멤버 가중 평균 중요도 상위 N.

값은 재학습마다 변하므로 **하드코딩하지 말고** 항상 `/model`로 읽어 표시한다(대략 test AUC ~0.76).

---

## 6. 관련 문서

- 앱 구조 → [01_app_structure.md](01_app_structure.md)
- 엔드포인트 → [03_endpoints.md](03_endpoints.md)
