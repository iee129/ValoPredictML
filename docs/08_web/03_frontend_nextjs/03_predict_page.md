# 03. 예측 페이지 (`/predict`)

핵심 시연 페이지. **맵 + 기준연도 + 팀당 5×{선수, 요원}** 을 입력받아 `POST /predict` 호출. 08_web 예측 페이지와의 결정적 차이는 **각 슬롯에 선수 입력이 있다**는 점.

---

## 1. UI 구조

```
┌──────────────────────────────────────────────────────────────┐
│  맵: [Ascent ▼]      기준 연도: [2026 ▼]                       │
├───────────────────────────────┬──────────────────────────────┤
│  팀 A                          │  팀 B                         │
│  슬롯1 [선수 ▾자동완성][요원 ▾] │  슬롯1 [선수 ▾][요원 ▾]        │
│  슬롯2 [선수 ▾][요원 ▾]         │  슬롯2 ...                     │
│  ... 5슬롯                      │  ... 5슬롯                     │
├───────────────────────────────┴──────────────────────────────┤
│                    [ 승률 예측하기 ]                          │
├──────────────────────────────────────────────────────────────┤
│  (예측 후)                                                     │
│  팀 A 62% ▰▰▰▰▱  |  팀 B 38% ▰▰▱▱▱     신뢰도 [HIGH]          │
│  역할군 레이더(A vs B)        영향 피처 바(top_features)        │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. 상태 (TypeScript)

```tsx
"use client";
import { useEffect, useState } from "react";
import { getOptions, predict } from "@/lib/api";
import type { Options, Slot, PredictResponse } from "@/types/api";

const EMPTY: Slot = { player: "", agent: "" };

export default function PredictPage() {
  const [opts, setOpts] = useState<Options | null>(null);
  const [map, setMap] = useState("");
  const [year, setYear] = useState<number>(0);
  const [teamA, setTeamA] = useState<Slot[]>(Array.from({ length: 5 }, () => ({ ...EMPTY })));
  const [teamB, setTeamB] = useState<Slot[]>(Array.from({ length: 5 }, () => ({ ...EMPTY })));
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getOptions().then((o) => {
      setOpts(o);
      setMap(o.maps[0]?.name ?? "");
      setYear(o.years[o.years.length - 1] ?? 0);   // 기본 = 최신(보통 max+1)
    }).catch((e) => setError(e.message));
  }, []);
  // ...
}
```

---

## 3. 슬롯 입력 (선수 + 요원)

```tsx
function setSlot(
  team: Slot[], setTeam: (s: Slot[]) => void,
  idx: number, patch: Partial<Slot>,
) {
  setTeam(team.map((s, i) => (i === idx ? { ...s, ...patch } : s)));
}

// LineupSlot.tsx 개념
// <input list="players" value={slot.player} onChange={e=>onChange({player:e.target.value})}/>
// <select value={slot.agent} onChange={e=>onChange({agent:e.target.value})}>
//   {agents.map(a => <option key={a.name} value={a.name}>{a.name} ({a.role})</option>)}
// </select>
```

- 선수: `<datalist>`(`opts.players`)로 자동완성. 자유 입력도 허용하되, 모르는 선수는 이전연도 이력이 비어 prior 피처가 0이 됨(모델은 동작함 — 단지 신호가 약해질 뿐).
- 요원: `opts.agents`(29종) 셀렉트.

---

## 4. 클라이언트 사전 검증 (백엔드 422를 미리 예방)

백엔드 `_validate_slots`와 동일 규칙을 UI에서도 막아 UX를 매끄럽게:

```ts
function validate(teamA: Slot[], teamB: Slot[]): string | null {
  const all = [...teamA, ...teamB];
  if (all.some(s => !s.player || !s.agent)) return "모든 슬롯에 선수와 요원을 선택하세요.";
  const players = all.map(s => s.player.trim().toLowerCase());
  if (new Set(players).size !== 10) return "10명의 선수는 서로 달라야 합니다.";
  for (const [name, team] of [["팀 A", teamA], ["팀 B", teamB]] as const) {
    const agents = team.map(s => s.agent);
    if (new Set(agents).size !== agents.length) return `${name} 안에서 같은 요원을 중복할 수 없습니다.`;
  }
  return null;
}
```

> 규칙 출처: `src/inference/predict.py` `_validate_slots`. 프론트 검증은 편의일 뿐, **최종 권위는 백엔드**다(우회 입력은 백엔드가 422로 차단).

---

## 5. 예측 호출

```tsx
async function onPredict() {
  const msg = validate(teamA, teamB);
  if (msg) { setError(msg); return; }
  setLoading(true); setError(null);
  try {
    const res = await predict({ map, cutoff_year: year, team_a: teamA, team_b: teamB });
    setResult(res);
  } catch (e) {
    setError((e as Error).message);   // FastAPI detail (한국어)
  } finally {
    setLoading(false);
  }
}
```

> 첫 호출은 콜드스타트로 수 초 걸릴 수 있다 → 로딩 스피너에 "이전 연도 기록을 계산 중입니다(첫 실행은 다소 걸립니다)" 문구 권장(폐기된 구 Streamlit 앱과 동일 안내).

---

## 6. 결과 렌더링 (`PredictResponse` 매핑)

```tsx
{result && (
  <section>
    <WinRateGauge label={result.team_a.name} p={result.team_a.win_probability} />
    <WinRateGauge label={result.team_b.name} p={result.team_b.win_probability} alt />
    <ConfidenceBadge confidence={result.confidence} />
    <RoleRadar a={result.role_counts.team_a} b={result.role_counts.team_b} />
    <FeatureBar items={result.top_features} />  {/* label/contribution 사용 */}
  </section>
)}
```

| UI 요소 | 사용 필드 |
|---------|-----------|
| 승률 게이지 | `team_a.win_probability`, `team_b.win_probability` |
| 예측 승자 강조 | `predicted_winner` ("A"/"B") |
| 신뢰도 배지 | `confidence` → `confidenceLevel()` |
| 역할군 레이더 | `role_counts.team_a` / `.team_b` (4역할) |
| 영향 피처 바 | `top_features[]`: `label`(표시), `contribution`(막대 길이) |
| 자연어 근거 카드 (C) | `explanations[]`: `text` 한국어 문장 |

> 위 결과 외에 **입력 단계**에서 부가 인사이트를 함께 띄운다: 맵 선택 시 요원 ✓/△/✗ 배지(`GET /agent-map-fit`), 5요원 완성 시 메타 매칭률 %(`POST /comp-match`), 구성 결함 경고(프론트 룰). 구현 → [../06_insights/00_overview.md](../06_insights/00_overview.md) §3(표시 타이밍).

---

## 7. 관련 문서

- 타입/클라이언트 → [02_types_and_api_client.md](02_types_and_api_client.md)
- 결과 컴포넌트 상세 → [04_pages_and_components.md](04_pages_and_components.md)
- 엔드포인트 → [../02_backend_fastapi/03_endpoints.md](../02_backend_fastapi/03_endpoints.md)
