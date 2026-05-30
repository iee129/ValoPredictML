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
| 피처 수 | `n_features` (125) |
| 성능 | `metrics.test_auc`, `metrics.test_acc`, `metrics.test_f1` |
| 검증 verdict | `validation.final_verdict` (PASS_TRUSTED_KAGGLE_ONLY_ADVANCED) |
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

발로란트 톤(레드 `#ff4655`, 다크 배경)은 기존 Streamlit 앱(`app/main.py`의 CSS 변수)이나 `docs/09_web/06_styling`의 비주얼 토큰을 참고해도 좋다. 단 **데이터 계약과 무관**하므로 시연 우선순위는 기능 → 스타일 순.

---

## 7. 관련 문서

- 예측 페이지 → [03_predict_page.md](03_predict_page.md)
- 엔드포인트 → [../02_backend_fastapi/03_endpoints.md](../02_backend_fastapi/03_endpoints.md)
- 시연 런북 → [../04_integration/02_demo_runbook.md](../04_integration/02_demo_runbook.md)
