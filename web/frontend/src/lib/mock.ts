// 프론트 내부 MOCK 데이터 + 빌더 — Route Handler(src/app/api/*)에서 사용.
// 실제 백엔드(web/backend) 없이 `npm run dev` 하나만으로 전체 UI가 동작하도록 한다.
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
  Jett: "duelist",
  Reyna: "duelist",
  Phoenix: "duelist",
  Raze: "duelist",
  Yoru: "duelist",
  Neon: "duelist",
  ISO: "duelist",
  Waylay: "duelist",
  Sova: "initiator",
  Breach: "initiator",
  Skye: "initiator",
  "KAY/O": "initiator",
  Fade: "initiator",
  Gekko: "initiator",
  Tejo: "initiator",
  Viper: "controller",
  Omen: "controller",
  Brimstone: "controller",
  Astra: "controller",
  Harbor: "controller",
  Clove: "controller",
  Miks: "controller",
  Killjoy: "sentinel",
  Cypher: "sentinel",
  Sage: "sentinel",
  Chamber: "sentinel",
  Deadlock: "sentinel",
  Vyse: "sentinel",
  Veto: "sentinel",
};
const AGENTS = Object.keys(AGENT_ROLE).sort(); // 29
const NEW_AGENTS = new Set(["Miks", "Veto", "Waylay"]);

const MAP_KO: Record<string, string> = {
  Ascent: "어센트",
  Bind: "바인드",
  Haven: "헤이븐",
  Split: "스플릿",
  Icebox: "아이스박스",
  Breeze: "브리즈",
  Fracture: "프랙처",
  Pearl: "펄",
  Lotus: "로터스",
  Sunset: "선셋",
  Abyss: "어비스",
  Drift: "드리프트",
  Corrode: "코로드",
};
const MAP_ORDER = Object.keys(MAP_KO);

const PLAYERS = [
  "TenZ",
  "aspas",
  "Derke",
  "Less",
  "Demon1",
  "yay",
  "Chronicle",
  "Boaster",
  "f0rsakeN",
  "Jinggg",
  "ZmjjKK",
  "nAts",
  "Sacy",
  "pancada",
  "saadhak",
  "Cryocells",
  "johnqt",
  "crashies",
  "Marved",
  "zekken",
  "tarik",
  "Zellsis",
  "trent",
  "valyn",
  "Mazino",
  "stax",
  "BuZz",
  "MaKo",
  "Rb",
  "Sayaplayer",
  "Alfajer",
  "Leo",
  "Sayf",
  "cNed",
  "starxo",
  "Wo0t",
  "Sheydos",
  "d3ffo",
  "trexx",
  "Redgar",
  "ardiis",
  "Jamppi",
  "keznit",
  "Klaus",
  "Melser",
  "Shyy",
  "heat",
  "Tacolilla",
  "NagZ",
  "kiNgg",
  "Khalil",
  "mwzera",
  "frz",
  "xand",
  "liazzi",
  "tuyz",
  "jzz",
  "Cortezia",
  "artzin",
  "raafa",
  "Jonn",
  "mazin",
  "Shao",
  "benjyfishy",
  "Patitek",
  "ANGE1",
  "Zyppan",
  "FNS",
  "Victor",
  "Ethan",
  "Boostio",
  "Verno",
  "C0M",
  "SUYGETSU",
  "Sheydos2",
];
const FEATURED_PLAYERS = [
  "stax",
  "BuZz",
  "MaKo",
  "Rb",
  "Sayaplayer",
].filter((player) => PLAYERS.includes(player));
const YEARS = [2021, 2022, 2023, 2024, 2025, 2026];

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
  const c: RoleCounts = {
    duelist: 0,
    initiator: 0,
    controller: 0,
    sentinel: 0,
  };
  for (const a of agents) {
    const r = AGENT_ROLE[a];
    if (r) c[r] += 1;
  }
  return c;
}

function balanceWarnings(rc: RoleCounts): BalanceWarning[] {
  const out: BalanceWarning[] = [];
  if (rc.controller === 0)
    out.push({
      code: "no_controller",
      severity: "high",
      message: "전략가 부재 — 스모크로 시야 차단·지역 통제가 약합니다.",
    });
  if (rc.sentinel >= 3)
    out.push({
      code: "too_many_sentinel",
      severity: "high",
      message: "감시자 과다 — 진입력이 부족해 공격 라운드가 어렵습니다.",
    });
  if (rc.duelist === 0)
    out.push({
      code: "no_duelist",
      severity: "medium",
      message: "타격대 부재 — 진입·킬 창출 주체가 없습니다.",
    });
  if (rc.initiator === 0)
    out.push({
      code: "no_initiator",
      severity: "medium",
      message: "척후대 부재 — 정보 수집·진입 보조가 약합니다.",
    });
  if (rc.duelist >= 4)
    out.push({
      code: "too_many_duelist",
      severity: "low",
      message: "타격대 과다 — 유틸·지역 통제가 부족합니다.",
    });
  return out;
}

const similarity = (u: number[], v: number[]) =>
  1 - u.reduce((s, x, i) => s + Math.abs(x - v[i]), 0) / 10;

// ── 엔드포인트 빌더 ────────────────────────────────────
export function mockHealth() {
  return {
    status: "ok",
    model_loaded: true,
    n_features: 179,
    contract: "advanced",
    mock: true,
  };
}

export function mockModel(): ModelInfo {
  const feats: [string, number][] = [
    ["a_prior_kd_mean", 0.052],
    ["b_prior_kd_mean", 0.048],
    ["a_synergy_mean", 0.041],
    ["a_map_agent_adr_mean", 0.038],
    ["a_prior_games_mean", 0.034],
    ["b_prior_kast_mean", 0.031],
    ["a_player_agent_kast_mean", 0.028],
    ["map_ascent", 0.022],
    ["a_role_controller_count", 0.019],
    ["b_synergy_mean", 0.017],
    ["a_prior_adr_mean", 0.015],
    ["b_map_agent_kd_mean", 0.013],
  ];
  // ROC 곡선 mock (선형 보간 + 약간의 굴곡)
  const fpr = [0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0];
  const tpr = [
    0, 0.12, 0.26, 0.38, 0.5, 0.65, 0.74, 0.81, 0.87, 0.91, 0.95, 0.98, 1.0,
  ];
  return {
    algorithm: "RF+XGB+LGBM_soft_voting (MOCK)",
    contract: "advanced",
    n_features: 179,
    metrics: {
      test_auc: 0.7009864514845388,
      test_acc: 0.6453622375879898,
      test_f1: 0.6478193628209094,
      train_auc: 0.7683689314137001,
      train_rows: 75405,
      test_rows: 16053,
      baseline_auc: 0.5943,
    },
    validation: { final_verdict: "신뢰 가능" },
    validation_summary: [
      { key: "forbidden_feature_count", label: "금지 피처", value: "0", passed: true },
      { key: "split_overlap_count", label: "split 중복", value: "0", passed: true },
      { key: "same_year_exclusion_check", label: "동일연도 제외", value: "정상", passed: true },
      { key: "source_prefix_check", label: "소스 계약", value: "정상", passed: true },
      { key: "test_auc_check", label: "Test AUC 게이트", value: "0.701", passed: true },
      { key: "final_verdict", label: "최종 판정", value: "신뢰 가능", passed: true },
    ],
    global_importance: feats.map(([feature, importance]) => ({
      feature,
      importance,
    })),
    eval: {
      primary_auc: 0.7009864514845388,
      primary_label: "Test AUC",
      secondary_auc: 0.7683689314137001,
      secondary_label: "Train AUC",
      note: "현재 웹 표시는 advanced train/test 맵 단위 승패 샘플 기준입니다.",
    },
    models: [
      {
        name: "RF",
        train_auc: 0.942,
        test_auc: 0.741,
        acc: 0.678,
        f1: 0.721,
        confusion_matrix: [
          [3120, 1480],
          [1240, 3160],
        ],
      },
      {
        name: "XGBoost",
        train_auc: 0.905,
        test_auc: 0.748,
        acc: 0.683,
        f1: 0.729,
        confusion_matrix: [
          [3180, 1420],
          [1190, 3210],
        ],
      },
      {
        name: "LightGBM",
        train_auc: 0.899,
        test_auc: 0.744,
        acc: 0.681,
        f1: 0.726,
        confusion_matrix: [
          [3150, 1450],
          [1210, 3190],
        ],
      },
      {
        name: "Ensemble",
        train_auc: 0.921,
        test_auc: 0.7009864514845388,
        acc: 0.696,
        f1: 0.74,
        confusion_matrix: [
          [3240, 1360],
          [1140, 3260],
        ],
      },
    ],
    roc: { fpr, tpr },
    eda: {
      sample_unit: "map_win_loss",
      sample_unit_label: "맵 단위 승패 샘플",
      sample_unit_note:
        "모델 학습·평가 기준은 맵별 승패 샘플입니다.",
      target_dist: [
        { label: 1, count: 46892 },
        { label: 0, count: 44566 },
      ],
      map_counts: [
        { map: "Ascent", count: 12400 },
        { map: "Haven", count: 11200 },
        { map: "Bind", count: 10800 },
        { map: "Split", count: 9600 },
        { map: "Lotus", count: 8900 },
        { map: "Icebox", count: 7800 },
        { map: "Sunset", count: 7200 },
        { map: "Fracture", count: 6500 },
        { map: "Pearl", count: 5900 },
        { map: "Breeze", count: 5100 },
        { map: "Abyss", count: 4800 },
      ],
      kd_winrate: Array.from({ length: 20 }, (_, i) => ({
        kd: parseFloat((0.5 + i * 0.075).toFixed(3)),
        wr: parseFloat((0.35 + i * 0.016).toFixed(3)),
      })),
      role_meta_by_year: [
        { year: 2021, role: "duelist", pick_rate: 0.42 },
        { year: 2021, role: "initiator", pick_rate: 0.28 },
        { year: 2021, role: "controller", pick_rate: 0.18 },
        { year: 2021, role: "sentinel", pick_rate: 0.12 },
        { year: 2022, role: "duelist", pick_rate: 0.38 },
        { year: 2022, role: "initiator", pick_rate: 0.31 },
        { year: 2022, role: "controller", pick_rate: 0.19 },
        { year: 2022, role: "sentinel", pick_rate: 0.12 },
        { year: 2023, role: "duelist", pick_rate: 0.35 },
        { year: 2023, role: "initiator", pick_rate: 0.33 },
        { year: 2023, role: "controller", pick_rate: 0.2 },
        { year: 2023, role: "sentinel", pick_rate: 0.12 },
        { year: 2024, role: "duelist", pick_rate: 0.32 },
        { year: 2024, role: "initiator", pick_rate: 0.35 },
        { year: 2024, role: "controller", pick_rate: 0.21 },
        { year: 2024, role: "sentinel", pick_rate: 0.12 },
      ],
    },
  };
}

export function mockOptions(): Options {
  const maps: MapInfo[] = MAP_ORDER.map((m) => ({ name: m, ko: MAP_KO[m] }));
  const agents: Agent[] = AGENTS.map((a) => ({ name: a, role: roleOf(a) }));
  return {
    maps,
    agents,
    players: PLAYERS,
    featured_players: FEATURED_PLAYERS,
    years: YEARS,
  };
}

export function mockAgentMapFit(map: string): AgentMapFitResponse {
  const agents = AGENTS.map((a) => {
    const role = roleOf(a);
    if (NEW_AGENTS.has(a)) {
      return {
        name: a,
        role,
        verdict: "ok" as const,
        pick_rate: null,
        win_rate: null,
        sample: 3,
        source: "rule" as const,
      };
    }
    // (맵×요원) 결정적 해시 — 균등 분포(비추천/보통/적합 ≈ 1:1:1).
    // 같은 맵·요원이면 항상 같고, 맵이나 요원을 바꾸면 바뀐다.
    const hh = h(map + "|" + a);
    const verdict: "fit" | "ok" | "weak" =
      hh < 0.34 ? "weak" : hh < 0.67 ? "ok" : "fit";
    return {
      name: a,
      role,
      verdict,
      pick_rate: r3(0.04 + h("pr" + map + a) * 0.55),
      win_rate: r3(0.42 + h("wr" + map + a) * 0.18),
      sample: Math.floor(40 + h("s" + map + a) * 1800),
      source: "data" as const,
    };
  });
  return { map, agents };
}

export function mockCompMatch(
  map: string,
  agents: string[],
): CompMatchResponse {
  const rc = roleCounts(agents);
  const u = [rc.duelist, rc.initiator, rc.controller, rc.sentinel];
  const nearest = [1, 2, 1, 1];
  const sim = similarity(u, nearest);
  const same = u.every((x, i) => x === nearest[i]);
  return {
    map,
    match_pct: r1(sim * 100),
    weighted_pct: r1(sim * 90),
    user_comp: rc,
    nearest_comp: { duelist: 1, initiator: 2, controller: 1, sentinel: 1 },
    nearest_win_share: 0.31,
    message: same
      ? "최다 승리 조합과 일치 (해당 메타 승리비중 31%)"
      : "메타 대비 역할 구성 일부 차이 (해당 메타 승리비중 31%)",
  };
}

function buildPrediction(
  mp: string,
  aIds: string[],
  bIds: string[],
  aAgents: string[],
  bAgents: string[],
  nameA = "팀 A",
  nameB = "팀 B",
  actual: number | null = null,
): PredictResponse {
  const rcA = roleCounts(aAgents);
  const rcB = roleCounts(bAgents);
  const raw =
    0.5 +
    (h(mp + aIds.join("|") + aAgents.join("|")) -
      h(bIds.join("|") + bAgents.join("|"))) *
      0.34;
  const probA = r4(Math.max(0.3, Math.min(0.7, raw)));
  const toA = probA >= 0.5;
  const winner = toA ? nameA : nameB;
  const sign = toA ? 1 : -1;

  const feats: [string, string, number, number][] = [
    ["a_prior_kd_mean", "A팀 이전 연도 선수 평균 K/D", 1.08, 0.052 * sign],
    [
      "a_prior_games_mean",
      "A팀 이전 연도 선수 평균 경기 수",
      42.0,
      0.041 * sign,
    ],
    ["a_synergy_mean", "A팀 선수 동료 경험 평균", 3.4, 0.034 * sign],
    [
      "a_map_agent_adr_mean",
      "A팀 맵-요원 이전 평균 평균 피해량",
      148.0,
      0.029 * -sign,
    ],
    [`map_${mp.toLowerCase()}`, `맵: ${MAP_KO[mp] ?? mp}`, 1.0, 0.018],
    [
      "a_player_agent_kast_mean",
      "A팀 선수-요원 이전 평균 KAST",
      0.72,
      0.015 * sign,
    ],
  ];
  const top_features = feats.map(([feature, label, value, con]) => ({
    feature,
    label,
    value,
    importance: Math.abs(con),
    contribution: r4(con),
  }));

  const dg = Math.floor(2 + h("g" + mp) * 8);
  const kd = Math.round((0.05 + h("kd" + mp) * 0.18) * 100) / 100;
  const explanations = [
    {
      feature: "prior_games",
      text: `${winner} 우세 요인: 직전 연도 경험이 평균 대비 ${dg}경기 많음`,
      magnitude: dg,
    },
    {
      feature: "prior_kd",
      text: `${winner} 우위: 선수 평균 K/D가 ${kd.toFixed(2)} 우세`,
      magnitude: kd,
    },
    {
      feature: "synergy",
      text: `${winner} 우위: 팀 동반 출전 경험(호흡)이 더 많음`,
      magnitude: 1.0,
    },
  ];

  const resp: PredictResponse = {
    map: mp,
    cutoff_year: null,
    predicted_winner: (toA ? "A" : "B") as Side,
    predicted_label: toA ? 1 : 0,
    confidence: r4(Math.abs(probA - 0.5) * 2),
    team_a: { name: nameA, win_probability: probA },
    team_b: { name: nameB, win_probability: r4(1 - probA) },
    role_counts: { team_a: rcA, team_b: rcB },
    top_features,
    model: { contract: "advanced", n_features: 179 },
    explanations,
    balance: { team_a: balanceWarnings(rcA), team_b: balanceWarnings(rcB) },
    match_key: null,
    actual_label: null,
    actual_winner: null,
    hit: null,
    lineup: {
      team_a: aIds.map((p, i) => ({ player: p, agent: aAgents[i] ?? "" })),
      team_b: bIds.map((p, i) => ({ player: p, agent: bAgents[i] ?? "" })),
    },
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
    mp,
    ta.map((s) => s.player),
    tb.map((s) => s.player),
    ta.map((s) => s.agent),
    tb.map((s) => s.agent),
  );
}

// ── 다시보기 (mock 경기 6건) ───────────────────────────
const REPLAY: [
  string,
  string,
  string,
  string,
  string,
  string[],
  string[],
  number,
][] = [
  [
    "mk_t1_geng_ascent",
    "2024-08-04",
    "Ascent",
    "T1",
    "GenG",
    ["Jett", "Sova", "Omen", "Killjoy", "KAY/O"],
    ["Raze", "Fade", "Viper", "Cypher", "Skye"],
    1,
  ],
  [
    "mk_drx_sen_bind",
    "2024-07-21",
    "Bind",
    "DRX",
    "Sentinels",
    ["Raze", "Gekko", "Brimstone", "Cypher", "Skye"],
    ["Jett", "Breach", "Viper", "Killjoy", "Fade"],
    0,
  ],
  [
    "mk_prx_fnc_haven",
    "2024-09-01",
    "Haven",
    "Paper Rex",
    "FNATIC",
    ["Jett", "Sova", "Omen", "Killjoy", "Breach"],
    ["Raze", "Fade", "Astra", "Cypher", "KAY/O"],
    1,
  ],
  [
    "mk_eg_nrg_split",
    "2024-06-15",
    "Split",
    "Evil Geniuses",
    "NRG",
    ["Raze", "Skye", "Omen", "Cypher", "Breach"],
    ["Jett", "Sova", "Viper", "Killjoy", "Gekko"],
    0,
  ],
  [
    "mk_kru_loud_lotus",
    "2024-08-25",
    "Lotus",
    "KRÜ",
    "LOUD",
    ["Raze", "Fade", "Omen", "Killjoy", "Sova"],
    ["Neon", "Breach", "Viper", "Cypher", "Skye"],
    1,
  ],
  [
    "mk_th_vit_icebox",
    "2024-07-07",
    "Icebox",
    "Team Heretics",
    "Team Vitality",
    ["Jett", "Sova", "Viper", "Killjoy", "Sage"],
    ["Raze", "Fade", "Harbor", "Cypher", "KAY/O"],
    0,
  ],
  [
    "mk_10_t1_geng",
    "2024-03-01",
    "Ascent",
    "T1",
    "GenG",
    ["Jett", "Sova", "Omen", "Killjoy", "KAY/O"],
    ["Raze", "Skye", "Omen", "Chamber", "KAY/O"],
    1,
  ],
  [
    "mk_11_drx_sentinels",
    "2024-04-06",
    "Bind",
    "DRX",
    "Sentinels",
    ["Raze", "Fade", "Viper", "Cypher", "Skye"],
    ["Jett", "Gekko", "Viper", "Sage", "Sova"],
    1,
  ],
  [
    "mk_12_paperrex_fnatic",
    "2024-05-11",
    "Haven",
    "Paper Rex",
    "FNATIC",
    ["Jett", "Breach", "Astra", "Killjoy", "Gekko"],
    ["Phoenix", "Breach", "Harbor", "Killjoy", "Fade"],
    0,
  ],
  [
    "mk_13_evilgeniuses_nrg",
    "2024-06-16",
    "Split",
    "Evil Geniuses",
    "NRG",
    ["Neon", "Sova", "Brimstone", "Cypher", "Fade"],
    ["Yoru", "Sova", "Astra", "Cypher", "Skye"],
    1,
  ],
  [
    "mk_14_kr_loud",
    "2024-07-21",
    "Icebox",
    "KRÜ",
    "LOUD",
    ["Raze", "Skye", "Omen", "Chamber", "KAY/O"],
    ["Raze", "Tejo", "Omen", "Vyse", "Sova"],
    0,
  ],
  [
    "mk_15_teamheretics_teamvitality",
    "2024-08-26",
    "Lotus",
    "Team Heretics",
    "Team Vitality",
    ["Jett", "Gekko", "Viper", "Sage", "Sova"],
    ["Jett", "Fade", "Clove", "Cypher", "KAY/O"],
    1,
  ],
  [
    "mk_16_edwardgaming_traceesports",
    "2024-09-05",
    "Sunset",
    "EDward Gaming",
    "Trace Esports",
    ["Phoenix", "Breach", "Harbor", "Killjoy", "Fade"],
    ["Jett", "Sova", "Omen", "Killjoy", "KAY/O"],
    1,
  ],
  [
    "mk_17_100thieves_cloud9",
    "2024-10-10",
    "Breeze",
    "100 Thieves",
    "Cloud9",
    ["Yoru", "Sova", "Astra", "Cypher", "Skye"],
    ["Raze", "Fade", "Viper", "Cypher", "Skye"],
    0,
  ],
  [
    "mk_18_leviatn_mibr",
    "2024-11-15",
    "Pearl",
    "LEVIATÁN",
    "MIBR",
    ["Raze", "Tejo", "Omen", "Vyse", "Sova"],
    ["Jett", "Breach", "Astra", "Killjoy", "Gekko"],
    1,
  ],
  [
    "mk_19_koi_karminecorp",
    "2024-03-20",
    "Fracture",
    "KOI",
    "Karmine Corp",
    ["Jett", "Fade", "Clove", "Cypher", "KAY/O"],
    ["Neon", "Sova", "Brimstone", "Cypher", "Fade"],
    0,
  ],
  [
    "mk_20_bilibiligaming_talon",
    "2024-04-25",
    "Abyss",
    "Bilibili Gaming",
    "Talon",
    ["Jett", "Sova", "Omen", "Killjoy", "KAY/O"],
    ["Raze", "Skye", "Omen", "Chamber", "KAY/O"],
    1,
  ],
  [
    "mk_21_t1_geng",
    "2024-05-04",
    "Ascent",
    "T1",
    "GenG",
    ["Raze", "Fade", "Viper", "Cypher", "Skye"],
    ["Jett", "Gekko", "Viper", "Sage", "Sova"],
    1,
  ],
  [
    "mk_22_drx_sentinels",
    "2024-06-09",
    "Bind",
    "DRX",
    "Sentinels",
    ["Jett", "Breach", "Astra", "Killjoy", "Gekko"],
    ["Phoenix", "Breach", "Harbor", "Killjoy", "Fade"],
    0,
  ],
  [
    "mk_23_paperrex_fnatic",
    "2024-07-14",
    "Haven",
    "Paper Rex",
    "FNATIC",
    ["Neon", "Sova", "Brimstone", "Cypher", "Fade"],
    ["Yoru", "Sova", "Astra", "Cypher", "Skye"],
    1,
  ],
  [
    "mk_24_evilgeniuses_nrg",
    "2024-08-19",
    "Split",
    "Evil Geniuses",
    "NRG",
    ["Raze", "Skye", "Omen", "Chamber", "KAY/O"],
    ["Raze", "Tejo", "Omen", "Vyse", "Sova"],
    0,
  ],
  [
    "mk_25_kr_loud",
    "2024-09-24",
    "Icebox",
    "KRÜ",
    "LOUD",
    ["Jett", "Gekko", "Viper", "Sage", "Sova"],
    ["Jett", "Fade", "Clove", "Cypher", "KAY/O"],
    1,
  ],
  [
    "mk_26_teamheretics_teamvitality",
    "2024-10-03",
    "Lotus",
    "Team Heretics",
    "Team Vitality",
    ["Phoenix", "Breach", "Harbor", "Killjoy", "Fade"],
    ["Jett", "Sova", "Omen", "Killjoy", "KAY/O"],
    1,
  ],
  [
    "mk_27_edwardgaming_traceesports",
    "2024-11-08",
    "Sunset",
    "EDward Gaming",
    "Trace Esports",
    ["Yoru", "Sova", "Astra", "Cypher", "Skye"],
    ["Raze", "Fade", "Viper", "Cypher", "Skye"],
    0,
  ],
];

export function mockReplayMatches(
  q = "",
  limit = 200,
): {
  items: ReplayMatch[];
  total: number;
} {
  const all: ReplayMatch[] = REPLAY.map(([mk, date, mp, ta, tb]) => ({
    match_key: mk,
    date,
    map: mp,
    team_a: ta,
    team_b: tb,
    label: `${date} | ${MAP_KO[mp] ?? mp} (${mp}) | ${ta} vs ${tb} | ${mk}`,
  }));
  const needle = q.trim().toLowerCase();
  const matched = needle
    ? all.filter((m) => {
        const hay =
          `${m.team_a} ${m.team_b} ${m.map} ${m.date} ${m.match_key}`.toLowerCase();
        return needle.split(/\s+/).every((t) => hay.includes(t));
      })
    : all;
  return { items: matched.slice(0, Math.max(0, limit)), total: matched.length };
}

export function mockReplayOne(key: string): PredictResponse | null {
  const m = REPLAY.find((r) => r[0] === key);
  if (!m) return null;
  const [, , mp, ta, tb, aa, ba, lab] = m;
  return buildPrediction(
    mp,
    [ta, ta, ta, ta, ta],
    [tb, tb, tb, tb, tb],
    aa,
    ba,
    ta,
    tb,
    lab,
  );
}
