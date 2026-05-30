# 01. 데이터 계약 (SSOT)

프론트(`types/api.ts`)와 백엔드(`valo_web_backend/schemas.py`)가 **반드시 일치**해야 하는 계약의 단일 출처. 모든 필드는 `app/predict.py`의 실제 동작에서 도출됐다.

---

## 1. 도메인 불변량 (`ml/`에서 확정 — 변경 불가)

| 항목 | 값 | 출처 |
|------|-----|------|
| 요원 수 | **29** | `AGENT_ROLE_MAP` (`ml/agent_roles.py`) |
| 역할군 | duelist / initiator / controller / sentinel | `ROLES` (`ml/valorant.py`) |
| 맵 수 | **13** | `MAP_ORDER` |
| 모델 입력 피처 | **정확히 125** | `FEATURE_COLS_ADVANCED` (import 시 어서션) |
| 학습/평가 소스 | `kaggle_*`만 | `SOURCE_CONTRACT` |
| 서빙 모델 | advanced 앙상블 1종 | `models/advanced/ensemble.joblib` |

맵 13종: Ascent, Bind, Haven, Split, Icebox, Breeze, Fracture, Pearl, Lotus, Sunset, Abyss, Drift, Corrode.

요원 29종(역할): **Duelist** Jett·Reyna·Phoenix·Raze·Yoru·Neon·ISO·Waylay / **Initiator** Sova·Breach·Skye·KAY/O·Fade·Gekko·Tejo / **Controller** Viper·Omen·Brimstone·Astra·Harbor·Clove·Miks / **Sentinel** Killjoy·Cypher·Sage·Chamber·Deadlock·Vyse·Veto.

---

## 2. 엔드포인트 ↔ `app.predict` 함수 매핑

| 엔드포인트 | 호출 함수 | 반환 |
|-----------|-----------|------|
| `POST /predict` | `predict_custom_lineup(map, cutoff_year, team_a_slots, team_b_slots)` | `PredictionResult` |
| `GET /replay/{key}` | `predict_replay_match(key)` | `PredictionResult` (+actual) |
| `GET /replay/matches` | `available_options()["replay_matches"]` | list |
| `GET /options` `/agents` `/maps` `/players` `/years` | `available_options()` | dict |
| `GET /model` | `load_model()`, `load_reports()`, `global_feature_importance()` | dict |
| `GET /agent-map-fit` | `reports/insights/agent_map_fit.json` (사전 집계) | dict |
| `POST /comp-match` | `reports/insights/meta_comps.json` (사전 집계) | dict |

> 인사이트(N·K·G·C) 계약은 [../06_insights/](../06_insights/00_overview.md)에서 별도 관리한다. 자연어 근거(C)는 `PredictResponse`에 `explanations: Explanation[]`를, 구성 결함(G)은 프론트 룰(+선택적 `balance`)을 추가한다.

---

## 3. `POST /predict` 계약 (확정)

### 요청
```ts
{
  map: string;            // 13종 화이트리스트
  cutoff_year: number;    // /years 범위 (예측 라인업의 "기준 연도")
  team_a: { player: string; agent: string }[];  // 정확히 5
  team_b: { player: string; agent: string }[];  // 정확히 5
}
```

검증(권위=백엔드 `_validate_slots`):
1. 각 팀 5슬롯
2. 선수 10명 전부 유일
3. 팀 내 요원 유일
4. map/agent 화이트리스트, cutoff_year 범위

### 응답
```ts
{
  map: string | null;
  cutoff_year?: number | null;
  predicted_winner: "A" | "B";   // predicted_label 1→A, 0→B
  predicted_label: number;
  confidence: number;            // abs(prob_a - 0.5) * 2
  team_a: { name: string; win_probability: number };
  team_b: { name: string; win_probability: number };  // = 1 - a
  role_counts: { team_a: RoleCounts; team_b: RoleCounts };
  top_features: { feature: string; label: string; value: number;
                  importance: number; contribution: number }[];
  model: { contract: string; n_features: number };
  // replay 전용:
  match_key?, actual_label?, actual_winner?, hit?
}
```

---

## 4. ⚠️ 흔한 계약 위반 (09_web에서 실제 발생)

| 위반 | 올바른 계약 |
|------|-------------|
| 요청에 선수 없이 요원만 보냄 | 슬롯마다 `player` 필수 (모델이 이전연도 스탯 조회) |
| `cutoff_year` 누락 | 필수 — 어느 연도 이전 이력을 쓸지 결정 |
| 응답 피처에 임의 라벨(`"팀 조합 다양성"`) | `feature`는 실제 컬럼명(`a_prior_kd_mean` 등), `label`은 `feature_label()` 결과 |
| `win_rate_a`/`win_rate_b` 같은 임의 키 | `team_a.win_probability` 구조 |
| 맵 10종 가정 | 13종 |
| 요원 역할 PascalCase 혼용 | canonical 소문자 4종 |

---

## 5. 변경 관리

계약을 바꿀 땐 **세 곳을 항상 함께**:
1. `valo_web_backend/schemas.py` (+ `serializers.py`)
2. `src/types/api.ts`
3. 본 문서(SSOT)

모델 피처/요원/맵이 바뀌면(`ml/` 변경) 1·2·3 모두 영향 → `tsc --noEmit` + 백엔드 `/health`·`/model`로 검증.

---

## 6. 관련 문서

- 백엔드 스키마 → [../02_backend_fastapi/04_schemas.md](../02_backend_fastapi/04_schemas.md)
- 프론트 타입 → [../03_frontend_nextjs/02_types_and_api_client.md](../03_frontend_nextjs/02_types_and_api_client.md)
- 시연 런북 → [02_demo_runbook.md](02_demo_runbook.md)
