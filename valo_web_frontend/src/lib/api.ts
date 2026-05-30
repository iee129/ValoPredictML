import type {
  Options, Agent, MapInfo, PredictRequest, PredictResponse,
  ReplayMatch, ModelInfo, AgentMapFitResponse, CompMatchResponse,
} from "@/types/api";

// 기본값 "/api" = 프론트 내부 mock(Route Handler, src/app/api/*). npm run dev 만으로 동작.
// 실제 백엔드 사용 시 .env.local 의 NEXT_PUBLIC_API_URL 을 "http://localhost:8000" 으로 설정.
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((body && body.detail) || `API ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const getOptions = () => apiFetch<Options>("/options");
export const getAgents = () => apiFetch<Agent[]>("/agents");
export const getMaps = () => apiFetch<MapInfo[]>("/maps");
export const getModel = () => apiFetch<ModelInfo>("/model");

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
