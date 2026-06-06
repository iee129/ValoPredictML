import type {
  Options,
  Agent,
  MapInfo,
  PredictRequest,
  PredictResponse,
  ReplayMatch,
  ModelInfo,
  AgentMapFitResponse,
  CompMatchResponse,
  HistoryDetailResponse,
  HistoryListResponse,
} from "@/types/api";

// "/api" = Next Route Handler가 FastAPI를 내부 프록시한다.
// 브라우저 진입점은 localhost:3000을 유지하고, 서버 전용 VALO_INTERNAL_API_URL로 백엔드 주소를 조정한다.
const BASE = "/api";

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
  apiFetch<PredictResponse>("/predict", {
    method: "POST",
    body: JSON.stringify(body),
  });

// q: 팀·맵·날짜·키 검색(공백=AND). total=전체 일치 수, items=상위 limit.
export const getReplayMatches = (opts?: { q?: string; limit?: number }) => {
  const params = new URLSearchParams();
  if (opts?.q?.trim()) params.set("q", opts.q.trim());
  params.set("limit", String(opts?.limit ?? 200));
  return apiFetch<{ items: ReplayMatch[]; total: number }>(
    `/replay/matches?${params.toString()}`,
  );
};

export const getReplay = (matchKey: string) =>
  apiFetch<PredictResponse>(`/replay/${encodeURIComponent(matchKey)}`);

export const getHistory = (opts?: { limit?: number; offset?: number }) => {
  const params = new URLSearchParams();
  params.set("limit", String(opts?.limit ?? 50));
  params.set("offset", String(opts?.offset ?? 0));
  return apiFetch<HistoryListResponse>(`/history?${params.toString()}`);
};

export const getHistoryDetail = (historyId: string) =>
  apiFetch<HistoryDetailResponse>(
    `/history/${encodeURIComponent(historyId)}`,
  );

// ── 인사이트 ─────────────────────────────────────────
export const getAgentMapFit = (map: string) =>
  apiFetch<AgentMapFitResponse>(
    `/agent-map-fit?map=${encodeURIComponent(map)}`,
  );

export const compMatch = (map: string, agents: string[]) =>
  apiFetch<CompMatchResponse>("/comp-match", {
    method: "POST",
    body: JSON.stringify({ map, agents }),
  });
