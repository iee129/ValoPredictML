# 00. 인사이트 기능 개요

기본 예측(맵 + 선수5·요원5 → 승률 + 근거) 위에 얹는 **사용자 체감 디테일**을 정의한다. 모두 현재 모델·데이터·도메인 룰 문서로 구현 가능한 것만 포함하며, **현재 구조로 불가능한 "선수 30/60/90일 픽 기록 경고"는 범위 외**(§4)다.

> 이 목록은 프로젝트가 이미 정의한 사용자 차별점(`docs/01_overview/01_project_summary.md` §6.1의 N·K·G·C·D)과 대응한다. 본 폴더는 그 중 **데이터 의존이 없는 N·K·G·C**를 구현 가능 기능으로 문서화하고, 외부 의존인 **D는 보류**한다.

---

## 1. 기능 ↔ 문서 ↔ 차별점 매핑

| 기능 | 차별점 | 문서 | 데이터 소스 | 형태 |
|------|:---:|------|-------------|------|
| 요원-맵 적합도 (슬롯 ✓/△/✗) | N | [01_agent_map_fit.md](01_agent_map_fit.md) | `matches.csv` 집계 + 도메인 룰 fallback | `GET /agent-map-fit` |
| 메타 조합 매칭률 % | K | [02_comp_match.md](02_comp_match.md) | `matches.csv` 승리 조합 마이닝 | `POST /comp-match` |
| 구성 결함 알림 | G | [03_balance_warning.md](03_balance_warning.md) | 순수 룰(역할 카운트) | 프론트 룰 + (선택) `/predict` |
| 자연어 승부 근거 | C | [04_nl_explanation.md](04_nl_explanation.md) | `top_features` + `feature_values` | `/predict` 응답 확장 |
| (오프라인) 사전 집계 빌더 | N·K 공통 | [05_precompute_and_data.md](05_precompute_and_data.md) | `src/insights/` 잡 | `reports/insights/*.json` |

기본 예측(맵 선택 / 입력·수정 / 예측·원인)은 이미 [../02_backend_fastapi/03_endpoints.md](../02_backend_fastapi/03_endpoints.md)의 `/maps`·`/predict`로 충족된다.

---

## 2. 계산 위치 분류 (중요)

| 분류 | 기능 | 콜드스타트 | 비고 |
|------|------|:---:|------|
| **오프라인 사전 집계** | 요원-맵 적합도, 메타 조합 | 없음 | `matches.csv` → JSON 1회 빌드, API는 JSON만 로드 |
| **요청 시 모델 추론** | 자연어 근거 | 첫 예측만 | `/predict` 결과에서 파생 |
| **프론트 즉시 룰** | 구성 결함 알림 | 없음 | 요원→역할 룩업만으로 입력 즉시 표시 |

핵심: 적합도·메타조합은 **모델 추론과 무관**하게 미리 만든 JSON에서 읽으므로 빠르고, 사용자가 슬롯을 고르는 즉시 표시할 수 있다. 모델의 무거운 이전연도 계산(`/predict` 콜드스타트)과 분리된다.

---

## 3. 표시 타이밍 (UX)

```
맵 선택
  └─ GET /agent-map-fit?map=Ascent   → 요원 셀렉트에 ✓/△/✗ 미리 표시 (N)
슬롯에 요원 채움 (선수+요원)
  ├─ 프론트 룰: 구성 결함 즉시 경고 (G)
  └─ POST /comp-match (디바운스)      → 메타 매칭률 % 표시 (K)
[예측] 클릭
  └─ POST /predict → 승률 + role_counts + top_features
       └─ explanations[] 한국어 근거 카드 (C)
```

적합도·결함·매칭률은 **예측 전에** 보여 입력을 돕고, 자연어 근거는 **예측 후** 결과를 풀이한다.

---

## 4. 범위 외 — 선수 30/60/90일 픽 경고 (차별점 D)

현재 구조로 **불가**. 사유:
- 모델 데이터(Kaggle)는 **연 단위 집계**이고 과거(2021–2024)라 "현재 기준 최근 N일" 픽 기록이 없다. `players.csv`엔 날짜도 없음(매치에만).
- 유일 소스는 VLR.gg API의 `/stats?timespan=30/60/90`인데 (a) 외부 자체호스팅 API, (b) 모델 제외된 "수집 중" 소스, (c) VLR ID ↔ Kaggle 선수명 매칭 문제. (구 `ml/vlrgg/*` 전용 모듈은 삭제됨 — raw 통합은 `data.ingest`가 담당.)

→ **VLR.gg 통합 모듈이 선행되어야 하며, 본 문서 세트에서는 보류**한다. 추후 진행 시 별도 `07_vlrgg_recent_picks/`로 문서화한다. (이전연도 기준 근사 — "해당 선수의 직전 연도 주력 요원이 아님" 경고 — 는 모델 데이터로 가능하나, 사용자가 요구한 30/60/90일 의미와 다르므로 별도 협의.)

---

## 5. 선결 조건

모든 인사이트는 `data/processed/matches.csv`(소스 `kaggle_*`)를 전제한다. 현재 로컬에 없으면 [../04_integration/02_demo_runbook.md](../04_integration/02_demo_runbook.md) §1 + [05_precompute_and_data.md](05_precompute_and_data.md)를 먼저 수행한다.

---

## 6. 관련 문서

- 데이터 계약 SSOT → [../04_integration/01_data_contract.md](../04_integration/01_data_contract.md)
- 엔드포인트 전체 → [../02_backend_fastapi/03_endpoints.md](../02_backend_fastapi/03_endpoints.md)
