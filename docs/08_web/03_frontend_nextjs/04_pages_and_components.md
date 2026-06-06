# 04. 그 외 페이지 · 컴포넌트

## 1. `/replay` — 경기 다시보기 (가장 안정적인 시연 경로)

`test.csv`의 실제 경기를 골라 모델 예측과 실제 결과를 대조한다. 피처가 이미 계산돼 있어 **콜드스타트가 없다** → 시연 도입부에 적합.

```tsx
"use client";
import { useEffect, useState } from "react";
import { getReplayMatches, getReplay } from "@/lib/api";
import type { ReplayMatch, PredictResponse } from "@/types/api";

export default function ReplayPage() {
  const [matches, setMatches] = useState<ReplayMatch[]>([]);
  const [picked, setPicked] = useState<string>("");
  const [result, setResult] = useState<PredictResponse | null>(null);

  useEffect(() => { getReplayMatches(200).then(r => setMatches(r.items)); }, []);

  async function onSelect(key: string) {
    setPicked(key);
    setResult(await getReplay(key));
  }
  // ...
}
```

결과 표시(추가 필드 사용):

| UI | 필드 |
|----|------|
| 예측 승자 | `predicted_winner` + `team_*.name`(실제 팀명) |
| 실제 승자 | `actual_winner` |
| 적중 여부 배지 | `hit` (true=적중/false=불일치) |
| 승률/역할/피처 | `/predict`와 동일 |

```tsx
<ReplayOutcome
  predicted={result.predicted_winner}
  actual={result.actual_winner!}
  hit={result.hit!}
  teamA={result.team_a} teamB={result.team_b}
/>
```

---

## 2. `/model` — 모델 근거

`GET /model` 한 번으로 채운다. 시연에서 "이 예측이 신뢰할 만한가"를 보여주는 페이지.

```tsx
const m = await getModel();   // ModelInfo
```

| 섹션 | 필드 |
|------|------|
| 알고리즘 | `algorithm` ("RF+XGB+LGBM_soft_voting") |
| 피처 수 | `n_features` (179) |
| 성능 | `metrics.test_auc`, `metrics.test_acc`, `metrics.test_f1` |
| 검증 verdict | `validation.final_verdict` (신뢰 가능) |
| 전역 피처 중요도 | `global_importance[]` (상위 N 바 차트) |

> 수치는 항상 API에서 읽는다(재학습 시 변동). 하드코딩 금지.

---

## 3. `/` — 홈

- 시연 흐름 3단계 안내(예측 / 다시보기 / 모델 근거)
- `GET /model`로 핵심 지표(test AUC, verdict) 요약 카드
- 각 페이지로의 내비게이션

---

## 4. 결과 시각화 컴포넌트 (Recharts)

| 컴포넌트 | Recharts | 입력 props |
|----------|----------|-----------|
| `WinRateGauge` | `RadialBarChart` | `p: number`(0~1), `label: string` |
| `RoleRadar` | `RadarChart` | `a: RoleCounts`, `b: RoleCounts` |
| `FeatureBar` | 커스텀 div 바 또는 `BarChart` | `items: FeatureContribution[]` |
| `ConfidenceBadge` | 없음 | `confidence: number` |

`RoleRadar` 데이터 변환 예:

```ts
const axes = (["duelist","initiator","controller","sentinel"] as const).map(role => ({
  role,
  A: a[role], B: b[role],
}));
```

`FeatureBar`는 `contribution`(부호 있음 — 음수는 팀 B 쪽 기여)을 막대 길이/방향으로, `label`을 축 텍스트로 사용.

---

## 5. 공통 UI

| 컴포넌트 | 역할 |
|----------|------|
| `ErrorBanner` | `catch`로 받은 메시지(FastAPI `detail`) 표시 |
| `Spinner` | 예측 로딩(특히 `/predict` 첫 호출 콜드스타트) |

에러 흐름은 모든 페이지 공통: `api.ts`가 `throw` → 페이지 `try/catch` → `setError` → `<ErrorBanner/>`.

---

## 6. 스타일 (선택)

발로란트 톤(레드 `#ff4655`, 다크 배경)은 `docs/08_web/06_styling`의 비주얼 토큰을 참고해도 좋다(폐기된 구 Streamlit 앱의 CSS 변수에서 계승된 팔레트). 단 **데이터 계약과 무관**하므로 시연 우선순위는 기능 → 스타일 순.

---

---

## 6. `/history` — 예측 기록

`GET /api/history`를 호출해 이전 예측 결과를 목록으로 보여준다. DB가 없으면 백엔드가 503을 반환하고, 프론트는 "히스토리를 사용할 수 없습니다" 안내를 표시한다.

```tsx
"use client";
import { useEffect, useState } from "react";
import type { HistoryListResponse, HistoryItem } from "@/types/api";

export default function HistoryPage() {
  const [data, setData] = useState<HistoryListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/history?limit=50")
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setData)
      .catch(e => setError(e.message));
  }, []);

  if (error) return <p>{error}</p>;
  if (!data)  return <p>로딩 중...</p>;
  // ...
}
```

| UI 항목 | 필드 |
|---------|------|
| 예측 시각 | `created_at` |
| 맵 / 기준연도 | `map`, `cutoff_year` |
| 예측 승자 | `predicted_winner` + `confidence` |
| 승률 | `team_a_win_probability`, `team_b_win_probability` |

상세 조회는 `GET /api/history/{id}`로 `request_json`·`response_json`까지 표시할 수 있다.

### `web/src/app/api/history/route.ts` — Next Route Handler

브라우저는 Next Route Handler(`/api/history`)를 호출하고, Route Handler가 `VALO_INTERNAL_API_URL`로 FastAPI를 프록시한다. 직접 FastAPI를 호출하지 않는다.

```ts
import { proxyGet } from "@/lib/serverApi";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  return proxyGet(`/history?${searchParams.toString()}`);
}
```

### Navbar 링크

`web/src/components/Navbar.tsx`(또는 동일 역할 레이아웃 컴포넌트)에 "히스토리" 링크가 `/history`로 추가돼 있다.

---

## 7. 관련 문서

- 예측 페이지 → [03_predict_page.md](03_predict_page.md)
- 엔드포인트 → [../02_backend_fastapi/03_endpoints.md](../02_backend_fastapi/03_endpoints.md)
- 히스토리·DB 상세 → [../02_backend_fastapi/06_history_and_db.md](../02_backend_fastapi/06_history_and_db.md)
- 시연 런북 → [../04_integration/02_demo_runbook.md](../04_integration/02_demo_runbook.md)
