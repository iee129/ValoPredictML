// 백엔드 web/backend/schemas.py 의 TS 거울 (SSOT).
// docs/09_web/03_frontend_nextjs/02_types_and_api_client.md

export type Role = "duelist" | "initiator" | "controller" | "sentinel";
export type Side = "A" | "B";

// ── GET /agents, /maps ──────────────────────────────
export interface Agent {
  name: string;
  role: Role;
}
export interface MapInfo {
  name: string;
  ko: string;
}

// ── GET /options ────────────────────────────────────
export interface Options {
  maps: MapInfo[];
  agents: Agent[];
  players: string[];
  featured_players?: string[];
  years: number[];
}

// ── POST /predict (요청) ────────────────────────────
export interface Slot {
  player: string;
  agent: string;
}
export interface PredictRequest {
  map: string;
  cutoff_year: number;
  team_a: Slot[];
  team_b: Slot[];
}

// ── 예측 응답 ───────────────────────────────────────
export interface TeamProb {
  name: string;
  win_probability: number;
}
export interface RoleCounts {
  duelist: number;
  initiator: number;
  controller: number;
  sentinel: number;
}
export interface FeatureContribution {
  feature: string;
  label: string;
  value: number;
  importance: number;
  contribution: number;
}
export interface Explanation {
  feature: string;
  text: string;
  magnitude: number;
}
export interface BalanceWarning {
  code: string;
  severity: "high" | "medium" | "low";
  message: string;
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
  // 실제 출전 라인업(다시보기 경기 조합용) — 동적
  lineup?: { team_a: Slot[]; team_b: Slot[] };
}

// ── GET /replay/matches ─────────────────────────────
export interface ReplayMatch {
  match_key: string;
  label: string;
  date: string;
  map: string;
  team_a: string;
  team_b: string;
  actual_label?: number | null;
  actual_winner?: Side | null;
}

// ── GET /model ──────────────────────────────────────
export interface PerModelMetrics {
  name: string;
  train_auc?: number;
  test_auc?: number;
  acc?: number;
  f1?: number;
  confusion_matrix?: [[number, number], [number, number]];
}
export interface ModelEval {
  primary_auc?: number;
  primary_label?: string;
  secondary_auc?: number;
  secondary_label?: string;
  random_auc?: number;
  chrono_auc?: number;
  note?: string;
}
export interface CVFold {
  name: string;
  auc: number;
}
export interface KdWinrate {
  kd: number;
  wr: number;
}
export interface RoleMetaYear {
  year: number;
  role: string;
  pick_rate: number;
}
export interface AgentMetaYear {
  year: number;
  agent: string;
  agent_key: string;
  pick_rate: number;
  win_rate: number;
  sample: number;
}
export interface FeatureGroupTopFeature {
  feature: string;
  importance: number;
  label: string;
}
export interface FeatureGroupImportance {
  group: string;
  label: string;
  importance: number;
  share: number;
  top_features: FeatureGroupTopFeature[];
}
export interface ConfidenceBin {
  bin: string;
  lower: number;
  upper: number;
  count: number;
  accuracy: number;
  avg_confidence: number;
}
export interface ValidationSummaryItem {
  key: string;
  label: string;
  value: string;
  passed: boolean;
}
export interface ModelInfo {
  algorithm: string;
  contract: string;
  n_features: number;
  metrics: {
    test_auc?: number;
    test_acc?: number;
    test_f1?: number;
    train_auc?: number;
    train_rows?: number;
    test_rows?: number;
    baseline_auc?: number;
    baseline_acc?: number;
    baseline_f1?: number;
    baseline_features?: number;
    [key: string]: unknown;
  };
  validation: { final_verdict?: string } & Record<string, unknown>;
  validation_summary?: ValidationSummaryItem[];
  global_importance: { feature: string; importance: number }[];
  // 백엔드가 실제 advanced 산출물에서 계산한 확장 필드
  eval?: ModelEval;
  models?: PerModelMetrics[];
  roc?: { fpr: number[]; tpr: number[] };
  cv?: { folds: CVFold[]; mean: number };
  feature_groups?: FeatureGroupImportance[];
  confidence_bins?: ConfidenceBin[];
  eda?: {
    sample_unit?: string;
    sample_unit_label?: string;
    sample_unit_note?: string;
    target_dist?: { label: number; count: number }[];
    map_counts?: { map: string; count: number }[];
    kd_winrate?: KdWinrate[];
    role_meta_by_year?: RoleMetaYear[];
    agent_meta_by_year?: AgentMetaYear[];
  };
}

// ── 인사이트 ─────────────────────────────────────────
export interface AgentFit {
  name: string;
  role: Role;
  verdict: "fit" | "ok" | "weak";
  pick_rate: number | null;
  win_rate: number | null;
  sample: number;
  source: "data" | "rule";
}
export interface AgentMapFitResponse {
  map: string;
  agents: AgentFit[];
}

export interface CompMatchResponse {
  map: string;
  match_pct: number;
  weighted_pct: number;
  user_comp: RoleCounts;
  nearest_comp: RoleCounts;
  nearest_win_share: number;
  message: string;
}
