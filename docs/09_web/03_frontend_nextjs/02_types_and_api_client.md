# 02. 타입 정의 · API 클라이언트

## 1. `src/types/api.ts` — 백엔드 스키마의 TS 거울

이 파일이 프론트의 단일 계약 출처다. 백엔드 `valo_web_backend/schemas.py`([../02_backend_fastapi/04_schemas.md](../02_backend_fastapi/04_schemas.md))와 필드명·타입이 정확히 일치해야 한다.

```ts
// src/types/api.ts

export type Role = "duelist" | "initiator" | "controller" | "sentinel";
export type Side = "A" | "B";

// ── GET /agents, /maps ──────────────────────────────
export interface Agent { name: string; role: Role }
export interface MapInfo { name: string; ko: string }

// ── GET /options ────────────────────────────────────
export interface Options {
  maps: MapInfo[];
  agents: Agent[];
  players: string[];
  years: number[];
}

// ── POST /predict (요청) ────────────────────────────
export interface Slot { player: string; agent: string }   // 선수 필수
export interface PredictRequest {
  map: string;
  cutoff_year: number;
  team_a: Slot[];   // 길이 5
  team_b: Slot[];   // 길이 5
}

// ── 예측 응답 (공통) ────────────────────────────────
export interface TeamProb { name: string; win_probability: number }
export interface RoleCounts { duelist: number; initiator: number; controller: number; sentinel: number }
export interface FeatureContribution {
  feature: string;       // 실제 컬럼명 (예: "a_prior_kd_mean")
  label: string;         // 한국어 라벨
  value: number;
  importance: number;
  contribution: number;
}
export interface PredictResponse {
  map: string | null;
  cutoff_year?: number | null;
  predicted_winner: Side;
  predicted_label: number;
  confidence: number;
  team_a: TeamProb;
  team_b: TeamProb;
  role_counts: { team_a: RoleCounts; team_b: RoleCounts };
  top_features: FeatureContribution[];
  model: { contract: string; n_features: number };
  explanations: Explanation[];                                      // 자연어 근거 (C)
  balance: { team_a: BalanceWarning[]; team_b: BalanceWarning[] };  // 구성 결함 (G)
  // replay 전용
  match_key?: string | null;
  actual_label?: number | null;
  actual_winner?: Side | null;
  hit?: boolean | null;
}

// ── GET /replay/matches ─────────────────────────────
export interface ReplayMatch {
  match_key: string; label: string;
  date: string; map: string; team_a: string; team_b: string;
}

// ── GET /model ──────────────────────────────────────
export interface ModelInfo {
  algorithm: string;
  contract: string;
  n_features: number;
  metrics: Record<string, number>;
  validation: { final_verdict: string } & Record<string, unknown>;
  global_importance: { feature: string; importance: number }[];
}

// ── 인사이트 (06_insights) ───────────────────────────
// GET /agent-map-fit (N)
export interface AgentFit {
  name: string; role: Role;
  verdict: "fit" | "ok" | "weak";          // ✓ / △ / ✗
  pick_rate: number | null; win_rate: number | null;
  sample: number; source: "data" | "rule";
}
export interface AgentMapFitResponse { map: string; agents: AgentFit[] }

// POST /comp-match (K)
export interface CompMatchResponse {
  map: string; match_pct: number; weighted_pct: number;
  user_comp: RoleCounts; nearest_comp: RoleCounts;
  nearest_win_share: number; message: string;
}

// PredictResponse.explanations / .balance (C, G)
export interface Explanation { feature: string; text: string; magnitude: number }
export interface BalanceWarning {
  code: string; severity: "high" | "medium" | "low"; message: string;
}
```

> **불변량을 타입으로 고정**: `Role` 유니온은 4종, `n_features`는 항상 125, `team_a/team_b`는 5슬롯. 09_web처럼 임의 필드(`"팀 조합 다양성"`)를 넣으면 컴파일 에러가 난다.

---

## 2. `src/lib/api.ts` — 타입 안전 fetch 래퍼

```ts
// src/lib/api.ts
import type {
  Options, Agent, MapInfo, PredictRequest, PredictResponse,
  ReplayMatch, ModelInfo, AgentMapFitResponse, CompMatchResponse,
} from "@/types/api";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    // FastAPI 에러는 {detail: "..."} 형태
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `API ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const getOptions   = () => apiFetch<Options>("/options");
export const getAgents    = () => apiFetch<Agent[]>("/agents");
export const getMaps      = () => apiFetch<MapInfo[]>("/maps");
export const getModel     = () => apiFetch<ModelInfo>("/model");

export const predict = (body: PredictRequest) =>
  apiFetch<PredictResponse>("/predict", { method: "POST", body: JSON.stringify(body) });

export const getReplayMatches = (limit = 200) =>
  apiFetch<{ items: ReplayMatch[]; total: number }>(`/replay/matches?limit=${limit}`);

export const getReplay = (matchKey: string) =>
  apiFetch<PredictResponse>(`/replay/${encodeURIComponent(matchKey)}`);

// ── 인사이트 ─────────────────────────────────────────
export const getAgentMapFit = (map: string) =>
  apiFetch<AgentMapFitResponse>(`/agent-map-fit?map=${encodeURIComponent(map)}`);

export const compMatch = (map: string, agents: string[]) =>
  apiFetch<CompMatchResponse>("/comp-match", {
    method: "POST", body: JSON.stringify({ map, agents }),
  });
```

- 제네릭 `apiFetch<T>`로 모든 호출이 응답 타입을 갖는다.
- FastAPI의 검증 실패(422)는 `{detail}` 문자열로 오므로 그대로 사용자에게 노출 가능(메시지가 한국어).

---

## 3. `src/lib/format.ts` — 표시 변환

```ts
export const pct = (p: number) => `${(p * 100).toFixed(1)}%`;

export const confidenceLevel = (c: number): "HIGH" | "MEDIUM" | "LOW" =>
  c >= 0.5 ? "HIGH" : c >= 0.2 ? "MEDIUM" : "LOW";

// confidence = abs(prob-0.5)*2 이므로 0~1. 위 임계값은 표시용(조정 가능).
```

> `confidence`의 정의(`abs(prob_a-0.5)*2`)는 백엔드 `PredictionResult` 그대로다. 레벨 임계값은 UI 표현일 뿐 모델과 무관.

---

## 4. 계약 변경 시 절차

1. 백엔드 `valo_web_backend/schemas.py` 수정
2. `src/types/api.ts` 동일하게 수정
3. `tsc --noEmit`로 깨지는 호출부 전수 확인
4. 계약 SSOT 문서 갱신 → [../04_integration/01_data_contract.md](../04_integration/01_data_contract.md)

---

## 5. 관련 문서

- 백엔드 스키마(원본) → [../02_backend_fastapi/04_schemas.md](../02_backend_fastapi/04_schemas.md)
- 예측 페이지에서의 사용 → [03_predict_page.md](03_predict_page.md)
