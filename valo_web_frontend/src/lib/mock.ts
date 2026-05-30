// 프론트 내부 MOCK 데이터 + 빌더 — Route Handler(src/app/api/*)에서 사용.
// 실제 백엔드(valo_web_backend) 없이 `npm run dev` 하나만으로 전체 UI가 동작하도록 한다.
// ⚠️ 시연/개발용 가짜값. 계약(필드명/타입)은 types/api.ts와 100% 동일.
// 실제 모델/데이터로 전환하려면 .env.local 의 NEXT_PUBLIC_API_URL 을 백엔드 주소로 바꾸면 된다.

import type {
  Agent,
  MapInfo,
  Options,
  PredictRequest,
  PredictResponse,
  ReplayMatch,
  ModelInfo,
  AgentMapFitResponse,
  CompMatchResponse,
  RoleCounts,
  BalanceWarning,
  Role,
  Side,
} from "@/types/api";

// ── 도메인 (요원 29 · 맵 13) ───────────────────────────
const AGENT_ROLE: Record<string, Role> = {
  Jett: "duelist", Reyna: "duelist", Phoenix: "duelist", Raze: "duelist",
  Yoru: "duelist", Neon: "duelist", ISO: "duelist", Waylay: "duelist",
  Sova: "initiator", Breach: "initiator", Skye: "initiator", "KAY/O": "initiator",
  Fade: "initiator", Gekko: "initiator", Tejo: "initiator",
  Viper: "controller", Omen: "controller", Brimstone: "controller", Astra: "controller",
  Harbor: "controller", Clove: "controller", Miks: "controller",
  Killjoy: "sentinel", Cypher: "sentinel", Sage: "sentinel", Chamber: "sentinel",
  Deadlock: "sentinel", Vyse: "sentinel", Veto: "sentinel",
};
const AGENTS = Object.keys(AGENT_ROLE).sort(); // 29
const NEW_AGENTS = new Set(["Miks", "Veto", "Waylay"]);

const MAP_KO: Record<string, string> = {
  Ascent: "어센트", Bind: "바인드", Haven: "헤이븐", Split: "스플릿",
  Icebox: "아이스박스", Breeze: "브리즈", Fracture: "프랙처", Pearl: "펄",
  Lotus: "로터스", Sunset: "선셋", Abyss: "어비스", Drift: "드리프트", Corrode: "코로드",
};
const MAP_ORDER = Object.keys(MAP_KO);

const PLAYERS = [
  "TenZ", "aspas", "Derke", "Less", "Demon1", "yay", "Chronicle", "Boaster",
  "f0rsakeN", "Jinggg", "ZmjjKK", "nAts", "Sacy", "pancada", "saadhak",
  "Cryocells", "johnqt", "crashies", "Marved", "zekken", "tarik", "Zellsis",
  "trent", "valyn", "Mazino", "stax", "BuZz", "MaKo", "Rb", "Sayaplayer",
];
const YEARS = [2021, 2022, 2023, 2024, 2025, 2026];
const ROLES: Role[] = ["duelist", "initiator", "controller", "sentinel"];

// 맵별 키픽/약체 (Ascent만 도메인 정확, 나머지는 hash 스프레드)
const KEY_PICKS: Record<string, { fit: Set<string>; weak: Set<string> }> = {
  Ascent: {
    fit: new Set(["Omen", "Sova", "Killjoy", "Jett", "KAY/O"]),
    weak: new Set(["Brimstone", "Phoenix"]),
  },
};

// ── 헬퍼 ──────────────────────────────────────────────
function h(s: string): number {
  let x = 0;
  for (let i = 0; i < s.length; i++) x = (x * 31 + s.charCodeAt(i)) >>> 0;
  return (x % 10000) / 10000;
}
const r1 = (n: number) => Math.round(n * 10) / 10;
const r3 = (n: number) => Math.round(n * 1000) / 1000;
const r4 = (n: number) => Math.round(n * 10000) / 10000;
const roleOf = (a: string): Role => AGENT_ROLE[a] ?? "duelist";

function roleCounts(agents: string[]): RoleCounts {
  const c: RoleCounts = { duelist: 0, initiator: 0, controller: 0, sentinel: 0 };
  for (const a of agents) {
    const r = AGENT_ROLE[a];
    if (r) c[r] += 1;
  }
  return c;
}

function balanceWarnings(rc: RoleCounts): BalanceWarning[] {
  const out: BalanceWarning[] = [];
  if (rc.controller === 0) out.push({ code: "no_controller", severity: "high", message: "전략가 부재 — 스모크로 시야 차단·지역 통제가 약합니다." });
  if (rc.sentinel >= 3) out.push({ code: "too_many_sentinel", severity: "high", message: "감시자 과다 — 진입력이 부족해 공격 라운드가 어렵습니다." });
  if (rc.duelist === 0) out.push({ code: "no_duelist", severity: "medium", message: "타격대 부재 — 진입·킬 창출 주체가 없습니다." });
  if (rc.initiator === 0) out.push({ code: "no_initiator", severity: "medium", message: "척후대 부재 — 정보 수집·진입 보조가 약합니다." });
  if (rc.duelist >= 4) out.push({ code: "too_many_duelist", severity: "low", message: "타격대 과다 — 유틸·지역 통제가 부족합니다." });
  return out;
}

const similarity = (u: number[], v: number[]) =>
  1 - u.reduce((s, x, i) => s + Math.abs(x - v[i]), 0) / 10;

// ── 엔드포인트 빌더 ────────────────────────────────────
export function mockHealth() {
  return { status: "ok", model_loaded: true, n_features: 125, contract: "advanced", mock: true };
}

export function mockModel(): ModelInfo {
  const feats: [string, number][] = [
    ["a_prior_kd_mean", 0.052], ["b_prior_kd_mean", 0.048], ["a_synergy_mean", 0.041],
    ["a_map_agent_adr_mean", 0.038], ["a_prior_games_mean", 0.034], ["b_prior_kast_mean", 0.031],
    ["a_player_agent_kast_mean", 0.028], ["map_ascent", 0.022], ["a_role_controller_count", 0.019],
    ["b_synergy_mean", 0.017], ["a_prior_adr_mean", 0.015], ["b_map_agent_kd_mean", 0.013],
  ];
  return {
    algorithm: "RF+XGB+LGBM_soft_voting (MOCK)", contract: "advanced", n_features: 125,
    metrics: { test_auc: 0.757, test_acc: 0.6958, test_f1: 0.7649 },
    validation: { final_verdict: "PASS_TRUSTED_KAGGLE_ONLY_ADVANCED" },
    global_importance: feats.map(([feature, importance]) => ({ feature, importance })),
  };
}

export function mockOptions(): Options {
  const maps: MapInfo[] = MAP_ORDER.map((m) => ({ name: m, ko: MAP_KO[m] }));
  const agents: Agent[] = AGENTS.map((a) => ({ name: a, role: roleOf(a) }));
  return { maps, agents, players: PLAYERS, years: YEARS };
}

export function mockAgentMapFit(map: string): AgentMapFitResponse {
  const rules = KEY_PICKS[map];
  const agents = AGENTS.map((a) => {
    const role = roleOf(a);
    if (NEW_AGENTS.has(a)) {
      return { name: a, role, verdict: "ok" as const, pick_rate: null, win_rate: null, sample: 3, source: "rule" as const };
    }
    let verdict: "fit" | "ok" | "weak";
    if (rules?.fit.has(a)) verdict = "fit";
    else if (rules?.weak.has(a)) verdict = "weak";
    else {
      const hh = h(map + a);
      verdict = hh < 0.3 ? "fit" : hh > 0.82 ? "weak" : "ok";
    }
    return {
      name: a, role, verdict,
      pick_rate: r3(0.04 + h("pr" + map + a) * 0.55),
      win_rate: r3(0.42 + h("wr" + map + a) * 0.18),
      sample: Math.floor(40 + h("s" + map + a) * 1800), source: "data" as const,
    };
  });
  return { map, agents };
}

export function mockCompMatch(map: string, agents: string[]): CompMatchResponse {
  const rc = roleCounts(agents);
  const u = [rc.duelist, rc.initiator, rc.controller, rc.sentinel];
  const nearest = [1, 2, 1, 1];
  const sim = similarity(u, nearest);
  const same = u.every((x, i) => x === nearest[i]);
  return {
    map, match_pct: r1(sim * 100), weighted_pct: r1(sim * 90),
    user_comp: rc, nearest_comp: { duelist: 1, initiator: 2, controller: 1, sentinel: 1 },
    nearest_win_share: 0.31,
    message: same
      ? "최다 승리 조합과 일치 (해당 메타 승리비중 31%)"
      : "메타 대비 역할 구성 일부 차이 (해당 메타 승리비중 31%)",
  };
}

function buildPrediction(
  mp: string, aIds: string[], bIds: string[], aAgents: string[], bAgents: string[],
  nameA = "팀 A", nameB = "팀 B", actual: number | null = null,
): PredictResponse {
  const rcA = roleCounts(aAgents);
  const rcB = roleCounts(bAgents);
  const raw = 0.5 + (h(mp + aIds.join("|") + aAgents.join("|")) - h(bIds.join("|") + bAgents.join("|"))) * 0.34;
  const probA = r4(Math.max(0.3, Math.min(0.7, raw)));
  const toA = probA >= 0.5;
  const winner = toA ? nameA : nameB;
  const sign = toA ? 1 : -1;

  const feats: [string, string, number, number][] = [
    ["a_prior_kd_mean", "A팀 이전 연도 선수 평균 K/D", 1.08, 0.052 * sign],
    ["a_prior_games_mean", "A팀 이전 연도 선수 평균 경기 수", 42.0, 0.041 * sign],
    ["a_synergy_mean", "A팀 선수 동료 경험 평균", 3.4, 0.034 * sign],
    ["a_map_agent_adr_mean", "A팀 맵-요원 이전 평균 평균 피해량", 148.0, 0.029 * -sign],
    [`map_${mp.toLowerCase()}`, `맵: ${MAP_KO[mp] ?? mp}`, 1.0, 0.018],
    ["a_player_agent_kast_mean", "A팀 선수-요원 이전 평균 KAST", 0.72, 0.015 * sign],
  ];
  const top_features = feats.map(([feature, label, value, con]) => ({
    feature, label, value, importance: Math.abs(con), contribution: r4(con),
  }));

  const dg = Math.floor(2 + h("g" + mp) * 8);
  const kd = Math.round((0.05 + h("kd" + mp) * 0.18) * 100) / 100;
  const explanations = [
    { feature: "prior_games", text: `${winner} 우세 요인: 직전 연도 경험이 평균 대비 ${dg}경기 많음`, magnitude: dg },
    { feature: "prior_kd", text: `${winner} 우위: 선수 평균 K/D가 ${kd.toFixed(2)} 우세`, magnitude: kd },
    { feature: "synergy", text: `${winner} 우위: 팀 동반 출전 경험(호흡)이 더 많음`, magnitude: 1.0 },
  ];

  const resp: PredictResponse = {
    map: mp, cutoff_year: null,
    predicted_winner: (toA ? "A" : "B") as Side, predicted_label: toA ? 1 : 0,
    confidence: r4(Math.abs(probA - 0.5) * 2),
    team_a: { name: nameA, win_probability: probA },
    team_b: { name: nameB, win_probability: r4(1 - probA) },
    role_counts: { team_a: rcA, team_b: rcB },
    top_features,
    model: { contract: "advanced", n_features: 125 },
    explanations,
    balance: { team_a: balanceWarnings(rcA), team_b: balanceWarnings(rcB) },
    match_key: null, actual_label: null, actual_winner: null, hit: null,
  };
  if (actual !== null) {
    resp.actual_label = actual;
    resp.actual_winner = (actual === 1 ? "A" : "B") as Side;
    resp.hit = resp.predicted_label === actual;
  }
  return resp;
}

export function mockPredict(body: PredictRequest): PredictResponse {
  const mp = body.map ?? "Ascent";
  const ta = body.team_a ?? [];
  const tb = body.team_b ?? [];
  return buildPrediction(
    mp, ta.map((s) => s.player), tb.map((s) => s.player),
    ta.map((s) => s.agent), tb.map((s) => s.agent),
  );
}

// ── 다시보기 (mock 경기 6건) ───────────────────────────
const REPLAY: [string, string, string, string, string, string[], string[], number][] = [
  ["mk_t1_geng_ascent", "2024-08-04", "Ascent", "T1", "GenG",
    ["Jett", "Sova", "Omen", "Killjoy", "KAY/O"], ["Raze", "Fade", "Viper", "Cypher", "Skye"], 1],
  ["mk_drx_sen_bind", "2024-07-21", "Bind", "DRX", "Sentinels",
    ["Raze", "Gekko", "Brimstone", "Cypher", "Skye"], ["Jett", "Breach", "Viper", "Killjoy", "Fade"], 0],
  ["mk_prx_fnc_haven", "2024-09-01", "Haven", "Paper Rex", "FNATIC",
    ["Jett", "Sova", "Omen", "Killjoy", "Breach"], ["Raze", "Fade", "Astra", "Cypher", "KAY/O"], 1],
  ["mk_eg_nrg_split", "2024-06-15", "Split", "Evil Geniuses", "NRG",
    ["Raze", "Skye", "Omen", "Cypher", "Breach"], ["Jett", "Sova", "Viper", "Killjoy", "Gekko"], 0],
  ["mk_kru_loud_lotus", "2024-08-25", "Lotus", "KRÜ", "LOUD",
    ["Raze", "Fade", "Omen", "Killjoy", "Sova"], ["Neon", "Breach", "Viper", "Cypher", "Skye"], 1],
  ["mk_th_vit_icebox", "2024-07-07", "Icebox", "Team Heretics", "Team Vitality",
    ["Jett", "Sova", "Viper", "Killjoy", "Sage"], ["Raze", "Fade", "Harbor", "Cypher", "KAY/O"], 0],
];

export function mockReplayMatches(limit = 200): { items: ReplayMatch[]; total: number } {
  const items: ReplayMatch[] = REPLAY.slice(0, limit).map(([mk, date, mp, ta, tb]) => ({
    match_key: mk, date, map: mp, team_a: ta, team_b: tb,
    label: `${date} | ${MAP_KO[mp] ?? mp} (${mp}) | ${ta} vs ${tb} | ${mk}`,
  }));
  return { items, total: items.length };
}

export function mockReplayOne(key: string): PredictResponse | null {
  const m = REPLAY.find((r) => r[0] === key);
  if (!m) return null;
  const [, , mp, ta, tb, aa, ba, lab] = m;
  return buildPrediction(mp, [ta, ta, ta, ta, ta], [tb, tb, tb, tb, tb], aa, ba, ta, tb, lab);
}
