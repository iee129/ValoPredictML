# 03. 엔드포인트 명세

기준 포트 `:8000`. 모든 응답 `application/json`. Swagger: `/docs`.

| 메서드 | 경로 | 설명 | 콜드스타트 |
|--------|------|------|------------|
| GET | `/health` | 헬스체크 + 모델 로드 여부 | 없음 |
| GET | `/model` | 모델 메타·지표·검증·전역 중요도 | 없음 |
| GET | `/options` | 입력 위젯용 번들(maps/agents/players/years) | 1회 |
| GET | `/agents` | 요원 29종 + 역할군 | 없음 |
| GET | `/maps` | 맵 13종 | 없음 |
| GET | `/players?limit=` | 선수 목록(빈도순) | 1회 |
| GET | `/years` | 선택 가능 기준연도 | 1회 |
| POST | `/predict` | 커스텀 5v5 예측 | 첫 호출만 |
| GET | `/replay/matches?limit=` | 다시보기 후보 경기 | 없음 |
| GET | `/replay/{match_key}` | 특정 경기 예측 vs 실제 | 없음 |
| GET | `/agent-map-fit?map=` | 요원-맵 적합도 ✓/△/✗ (N) | 없음 |
| POST | `/comp-match` | 메타 조합 매칭률 % (K) | 없음 |

> 인사이트 엔드포인트(`/agent-map-fit`, `/comp-match`)는 모델 추론이 아니라 사전 집계 JSON(`reports/insights/*.json`)을 읽으므로 콜드스타트가 없다. 명세는 [../06_insights/](../06_insights/00_overview.md) 참조. 구성 결함 알림(G)은 프론트 룰, 자연어 근거(C)는 `/predict` 응답의 `explanations[]`로 제공된다.

---

## GET /health

```json
{ "status": "ok", "model_loaded": true, "n_features": 125, "contract": "advanced" }
```
`load_model()`의 `n_features_in_`이 125가 아니면 `model_loaded=false`로 표기(앱 `load_model`은 불일치 시 `ValueError`를 던지므로 503 처리).

---

## GET /model

`load_model()` + `load_reports()` + `global_feature_importance()` 직렬화.

```json
{
  "algorithm": "RF+XGB+LGBM_soft_voting",
  "contract": "advanced",
  "n_features": 125,
  "metrics": { "test_auc": 0.7570, "test_acc": 0.6958, "test_f1": 0.7649 },
  "validation": { "final_verdict": "PASS_TRUSTED_KAGGLE_ONLY_ADVANCED" },
  "global_importance": [
    { "feature": "a_prior_kd_mean", "importance": 0.041 }
  ]
}
```
> `metrics`/`validation` 키는 `reports/*.json` 원본 구조를 그대로 노출하거나 위처럼 일부만 추려도 된다. 수치는 파일에서 읽은 값(예시일 뿐).

---

## GET /agents

`available_options()["agents"]`(canonical 이름) + `AGENT_ROLE_MAP` 역할 결합. 29종.

```json
[
  { "name": "Jett", "role": "duelist" },
  { "name": "Sova", "role": "initiator" },
  { "name": "Omen", "role": "controller" },
  { "name": "Killjoy", "role": "sentinel" },
  { "name": "Miks", "role": "controller" }
]
```
역할 라벨은 canonical 소문자(`duelist|initiator|controller|sentinel`)로 정규화 권장(원본 `AGENT_ROLE_MAP`은 "Duelist" 등 PascalCase).

---

## GET /maps

`available_options()["maps"]` — `MAP_ORDER` 중 데이터에 등장하는 맵. 한국어 라벨 동봉 권장.

```json
[
  { "name": "Ascent", "ko": "어센트" },
  { "name": "Corrode", "ko": "코로드" }
]
```
전체 13종: Ascent, Bind, Haven, Split, Icebox, Breeze, Fracture, Pearl, Lotus, Sunset, Abyss, Drift, Corrode. (ko 매핑 출처: `app/predict.py` `MAP_LABELS`)

---

## GET /players?limit=300

`available_options()["players"]` — kaggle 소스 선수 빈도 내림차순. 선수 자동완성/셀렉트용.

```json
{ "players": ["TenZ", "aspas", "Derke", "..."], "total": 1234 }
```

---

## GET /years

`available_options()["years"]` — 데이터 등장 연도 + (최댓값+1). 기준연도(`cutoff_year`)는 이 목록에서 고른다. "미래" 라인업 예측은 최댓값+1(예: 2026) 선택.

```json
{ "years": [2021, 2022, 2023, 2024, 2025, 2026], "default": 2026 }
```

---

## POST /predict

### Request

```json
{
  "map": "Ascent",
  "cutoff_year": 2026,
  "team_a": [
    { "player": "TenZ",   "agent": "Jett" },
    { "player": "Sacy",   "agent": "Sova" },
    { "player": "pancada","agent": "Omen" },
    { "player": "Less",   "agent": "Killjoy" },
    { "player": "saadhak","agent": "Fade" }
  ],
  "team_b": [
    { "player": "aspas",  "agent": "Reyna" },
    { "player": "Cauanzin","agent": "Breach" },
    { "player": "tuyz",   "agent": "Viper" },
    { "player": "Mazino", "agent": "Cypher" },
    { "player": "Khalil", "agent": "Skye" }
  ]
}
```

검증 규칙(= `_validate_slots`):
- `team_a`·`team_b` 각각 정확히 5개
- 10명 선수 식별자 전부 유일(중복 불가)
- 같은 팀 안에서 요원 중복 불가
- `map`은 13종 화이트리스트, `agent`는 29종 화이트리스트, `cutoff_year`는 `/years` 범위

### Response (`PredictResponse`)

```json
{
  "map": "Ascent",
  "cutoff_year": 2026,
  "predicted_winner": "A",
  "predicted_label": 1,
  "confidence": 0.24,
  "team_a": { "name": "팀 A", "win_probability": 0.62 },
  "team_b": { "name": "팀 B", "win_probability": 0.38 },
  "role_counts": {
    "team_a": { "duelist": 2, "initiator": 1, "controller": 1, "sentinel": 1 },
    "team_b": { "duelist": 1, "initiator": 2, "controller": 1, "sentinel": 1 }
  },
  "top_features": [
    { "feature": "a_prior_kd_mean", "label": "A팀 이전 연도 선수 평균 K/D",
      "value": 1.05, "importance": 0.031, "contribution": 0.033 }
  ],
  "model": { "contract": "advanced", "n_features": 125 }
}
```

필드 ↔ `PredictionResult` 매핑은 [04_schemas.md](04_schemas.md) §2.

---

## GET /replay/matches?limit=200

`predict_replay_match`이 다루는 `test.csv` 후보 목록(`available_options()["replay_matches"]` 형식 확장).

```json
{
  "items": [
    { "match_key": "a1b2...", "label": "2024-05-01 | 어센트 (Ascent) | T1 vs GenG | a1b2...",
      "date": "2024-05-01", "map": "Ascent", "team_a": "T1", "team_b": "GenG" }
  ],
  "total": 200
}
```

---

## GET /replay/{match_key}

`predict_replay_match(match_key)` 직렬화. `PredictResponse` + 다음 필드 추가:

```json
{
  "match_key": "a1b2...",
  "actual_label": 1,
  "actual_winner": "A",
  "hit": true,
  "team_a": { "name": "T1", "win_probability": 0.58 },
  "team_b": { "name": "GenG", "win_probability": 0.42 }
}
```
`hit = (predicted_label == actual_label)`. 없는 `match_key`는 404. (실제 팀명이 `team_a.name`/`team_b.name`에 들어간다.)

---

## 관련 문서

- 스키마 정의 → [04_schemas.md](04_schemas.md)
- 실행·CORS → [05_run_and_cors.md](05_run_and_cors.md)
- 프론트 타입 → [../03_frontend_nextjs/02_types_and_api_client.md](../03_frontend_nextjs/02_types_and_api_client.md)
