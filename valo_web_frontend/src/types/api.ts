// 백엔드 valo_web_backend/schemas.py 의 TS 거울 (SSOT).
// docs_web/03_frontend_nextjs/02_types_and_api_client.md

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
export interface Slot { player: string; agent: string }
export interface PredictRequest {
  map: string;
  cutoff_year: number;
  team_a: Slot[];
  team_b: Slot[];
}

// ── 예측 응답 ───────────────────────────────────────
export interface TeamProb { name: string; win_probability: number }
export interface RoleCounts {
  duelist: number; initiator: number; controller: number; sentinel: number;
}
export interface FeatureContribution {
  feature: string; label: string;
  value: number; importance: number; contribution: number;
}
export interface Explanation { feature: string; text: string; magnitude: number }
export interface BalanceWarning {
  code: string; severity: "high" | "medium" | "low"; message: string;
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
  explanations: Explanation[];
  balance: { team_a: BalanceWarning[]; team_b: BalanceWarning[] };
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
  validation: { final_verdict?: string } & Record<string, unknown>;
  global_importance: { feature: string; importance: number }[];
}

// ── 인사이트 ─────────────────────────────────────────
export interface AgentFit {
  name: string; role: Role;
  verdict: "fit" | "ok" | "weak";
  pick_rate: number | null; win_rate: number | null;
  sample: number; source: "data" | "rule";
}
export interface AgentMapFitResponse { map: string; agents: AgentFit[] }

export interface CompMatchResponse {
  map: string; match_pct: number; weighted_pct: number;
  user_comp: RoleCounts; nearest_comp: RoleCounts;
  nearest_win_share: number; message: string;
}
