# 03. 컴포넌트 시각·props 명세

각 컴포넌트의 props(타입은 `types/api.ts` 재사용)와 시각 규칙. 색 의미는 [00_design_principles.md](00_design_principles.md) §3 고정 규약을 따른다.

---

## 1. 입력 컴포넌트

### `LineupSlot` — 선수+요원 한 쌍 + 적합도 배지
```ts
props: {
  side: "A" | "B";
  value: Slot;                       // {player, agent}
  players: string[];                 // datalist 자동완성
  agents: Agent[];                   // 셀렉트
  fit?: AgentFit;                    // 적합도 (요원 선택 시)
  onChange: (patch: Partial<Slot>) => void;
}
```
- 선수: `<input list>` 자동완성 / 요원: `<select>`
- 요원 옆 **적합도 배지**(아래 §2 FitBadge)
- 슬롯 테두리: side A=레드, B=시안. 적합도 ✗면 테두리 앰버 경고 + 툴팁
- 빈 슬롯: 점선 테두리 `--color-line`

### `MapSelect` / `YearSelect`
상단 바 드롭다운. 맵은 `{name, ko}` → "어센트 (Ascent)" 표기.

---

## 2. 인사이트 컴포넌트 (예측 전 표시)

### `FitBadge` — 요원-맵 적합도 ✓/△/✗ (N)
```ts
props: { fit: AgentFit }    // verdict, pick_rate, source
```
| verdict | 기호 | 색 | 텍스트 | 툴팁 |
|:---:|:---:|----|--------|------|
| `fit` | ✓ | green | 적합 | "픽률 {pick_rate%} (표본 {sample})" |
| `ok` | △ | muted | 보통 | 표본 부족이면 "데이터 적음" |
| `weak` | ✗ | red | 비추천 | "이 맵에서 드묾 {pick_rate%}" |

> **색+기호+텍스트 3중 인코딩**(색맹 대응). `source:"rule"`이면 배지에 작은 "룰" 점 표기.

### `MetaMatchBar` — 메타 조합 매칭률 % (K)
```ts
props: { result: CompMatchResponse; side: "A"|"B" }
```
- 큰 숫자 `match_pct%` + 진행 바(side 색)
- 하단 `message` 한 줄("승리 조합 1위와 역할 한 자리 차이")
- `weighted_pct`는 작게 보조

### `BalanceAlert` — 구성 결함 (G)
```ts
props: { warnings: BalanceWarning[] }   // 프론트 balanceCheck() 또는 응답 balance
```
- severity별 칩: high=red, medium=amber, low=muted
- 결함 없으면 "구성 균형 양호 ✅"(green) 한 줄 — 빈 영역 방지
- 칩에 기호(⚠) + 메시지

---

## 3. 결과 컴포넌트 (예측 후)

### `WinnerCard` — 예측 승자 (가장 큼)
```ts
props: { winner: "A"|"B"; teamName: string; pct: number }
```
- 승자 팀명 + 승률 % 를 `--font-display` `clamp(2.5rem,5vw,4rem)`
- 배경 틴트: A=red-soft, B=cyan-soft. tactical-cut 적용.

### `WinRateGauge` — 승률 게이지 (Recharts RadialBar)
```ts
props: { label: string; p: number; side: "A"|"B" }
```
- 0~1 → 도넛 채움, side 색. 중앙 `pct(p)`.
- 두 게이지(A·B) 나란히.

### `ConfidenceBadge`
```ts
props: { confidence: number }   // abs(prob-0.5)*2
```
HIGH(≥.5 green) / MEDIUM(≥.2 amber) / LOW(muted). 기호+텍스트.

### `RoleRadar` — 역할 구성 비교 (Recharts Radar)
```ts
props: { a: RoleCounts; b: RoleCounts }
```
4축(타격대/척후대/전략가/감시자). A=레드 폴리곤, B=시안 폴리곤 오버레이.

### `FeatureBar` — 영향 피처 (top_features)
```ts
props: { items: FeatureContribution[] }
```
- 수평 바, 길이=`|contribution|`, 라벨=`label`(한국어)
- 부호: 양수(A 기여)=레드, 음수(B 기여)=시안 → 방향으로 어느 팀에 유리한지 표현

### `ReasonCard` — 자연어 근거 (C)
```ts
props: { winner: "A"|"B"; teamName: string; explanations: Explanation[] }
```
- 헤더 "{팀명} 우세"
- `explanations[].text` 2~4개를 불릿으로(Pretendard, 또렷)
- 비어 있으면 카드 자체 숨김

### `ReplayOutcome` — 예측 vs 실제 (replay)
```ts
props: { predicted: "A"|"B"; actual: "A"|"B"; hit: boolean; teamA: TeamProb; teamB: TeamProb }
```
- `hit` → "적중 ✅"(green) / "불일치 ✗"(red) 대형 배지

---

## 4. 공통 UI

| 컴포넌트 | props | 시각 |
|----------|-------|------|
| `Legend` | `—` | ✓적합 △보통 ✗비추 항상 표시(우 상단) |
| `ErrorBanner` | `{message}` | red-soft 배경, FastAPI `detail` 노출 |
| `Spinner` | `{label?}` | 예측 첫 호출 "이전 연도 기록 계산 중…" |
| `MetricCard` | `{label, value}` | `/model` 페이지 숫자 카드 |

---

## 5. 컴포넌트 ↔ 데이터 출처 요약

| 컴포넌트 | 데이터 | 엔드포인트 |
|----------|--------|------------|
| FitBadge | `AgentFit` | `GET /agent-map-fit` |
| MetaMatchBar | `CompMatchResponse` | `POST /comp-match` |
| BalanceAlert | `BalanceWarning[]` | 프론트 룰 / `/predict.balance` |
| Winner/Gauge/Radar/FeatureBar | `PredictResponse` | `POST /predict` |
| ReasonCard | `Explanation[]` | `POST /predict.explanations` |
| ReplayOutcome | `PredictResponse`(+actual) | `GET /replay/{key}` |

---

## 6. 관련 문서

- 레이아웃 → [02_layout_demo_dashboard.md](02_layout_demo_dashboard.md)
- 타입 정의 → [../03_frontend_nextjs/02_types_and_api_client.md](../03_frontend_nextjs/02_types_and_api_client.md)
- 인사이트 계산 → [../06_insights/00_overview.md](../06_insights/00_overview.md)
