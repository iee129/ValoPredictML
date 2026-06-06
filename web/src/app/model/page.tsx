"use client";

import { useEffect, useState } from "react";
import { getModel } from "@/lib/api";
import type {
  AgentMetaYear,
  ModelInfo,
  PerModelMetrics,
  RoleMetaYear,
} from "@/types/api";
import ErrorBanner from "@/components/ui/ErrorBanner";
import Spinner from "@/components/ui/Spinner";
import PageBackdrop from "@/components/ui/PageBackdrop";
import RocCurve from "@/components/charts/RocCurve";
import ConfusionMatrix from "@/components/charts/ConfusionMatrix";
import Donut from "@/components/charts/Donut";
import GroupedColumns from "@/components/charts/GroupedColumns";
import { CornerAccent, SectionKicker } from "@/components/ui/Tactical";

// ── 공통 UI ─────────────────────────────────────────────

// 섹션 그룹 헤더 ( // 일반화 진단 형태 — 카드 바깥 )
function SectionHeader({ children }: { children: React.ReactNode }) {
  return <SectionKicker className="mt-1">{children}</SectionKicker>;
}

// 카드 제목 (붉은 세로 틱 + 제목 + 선택 부제) — 시안의 카드 헤더
function CardTitle({
  children,
  sub,
}: {
  children: React.ReactNode;
  sub?: string;
}) {
  return (
    <div className="mb-3">
      <div className="flex items-center gap-2">
        <span
          aria-hidden="true"
          className="inline-block w-[3px] h-[13px] rounded-sm bg-red shrink-0"
        />
        <h3 className="text-sm font-extrabold text-ink leading-none">
          {children}
        </h3>
      </div>
      {sub && <p className="mt-1.5 text-xs text-muted">{sub}</p>}
    </div>
  );
}

function Card({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`tactical-card tactical-depth relative overflow-hidden rounded-[var(--radius)] border border-line bg-panel-2/60 p-4 shadow-[var(--shadow-card)] ${className}`}
    >
      <CornerAccent />
      {children}
    </div>
  );
}

// 가로 막대 (모델 비교 · 피처 중요도 · 타겟 분포 · 맵별 승패 샘플 수 공용)
function HBar({
  label,
  value,
  pct,
  color = "var(--color-red)",
  strong = false,
}: {
  label: string;
  value: string;
  pct: number;
  color?: string;
  strong?: boolean;
}) {
  return (
    <div className="text-xs">
      <div className="flex items-center justify-between gap-2 mb-1">
        <span
          className={`truncate ${strong ? "text-ink font-bold" : "text-muted"}`}
        >
          {label}
        </span>
        <span className="tabular-nums shrink-0 font-bold text-ink">
          {value}
        </span>
      </div>
      <div className="h-2 rounded bg-white/10 overflow-hidden">
        <div
          className="h-full rounded"
          style={{
            width: `${Math.max(0, Math.min(100, pct))}%`,
            background: color,
          }}
        />
      </div>
    </div>
  );
}

// ── 도메인 헬퍼 ─────────────────────────────────────────

// AUC 막대 길이 — 0.60~0.80 구간을 0~100%로 매핑해 모델 간 차이를 부각
const aucPct = (auc: number, lo = 0.6, hi = 0.8) =>
  ((auc - lo) / (hi - lo)) * 100;

// 모델 표시명 보정
const MODEL_KO: Record<string, string> = {
  RF: "Random Forest",
  XGBoost: "XGBoost",
  LightGBM: "LightGBM",
  Ensemble: "앙상블 (Soft Voting)",
};

// 역할군 한국어 축약 (EDA 범례용)
const ROLE_SHORT: Record<string, string> = {
  duelist: "타격",
  initiator: "척후",
  controller: "전략",
  sentinel: "감시",
};
const ROLE_COLOR: Record<string, string> = {
  duelist: "var(--color-valo-duelist)",
  initiator: "var(--color-valo-initiator)",
  controller: "var(--color-valo-controller)",
  sentinel: "var(--color-valo-sentinel)",
};
const AGENT_META_COLORS = [
  "var(--color-red)",
  "var(--color-cyan)",
  "var(--color-green)",
  "var(--color-amber)",
  "var(--color-valo-initiator)",
  "var(--color-valo-controller)",
];
const FEATURE_GROUP_COLORS = [
  "var(--color-red)",
  "var(--color-cyan)",
  "var(--color-green)",
  "var(--color-amber)",
  "var(--color-valo-initiator)",
  "var(--color-valo-controller)",
  "var(--color-valo-sentinel)",
  "var(--color-muted)",
];

// 전역 피처 중요도의 원시 컬럼명 → 한국어 의미 라벨
function featureLabel(raw: string): string {
  const f = raw.toLowerCase();
  if (f.includes("map_agent")) return "맵×요원 적합도";
  if (f.includes("player_agent")) return "선수×요원 숙련";
  if (f.includes("prior_adr") || (f.includes("adr") && f.includes("prior")))
    return "이전연도 평균 ADR";
  if (f.includes("prior_kast")) return "이전연도 KAST";
  if (f.includes("synergy")) return "팀 시너지";
  if (f.includes("prior_games") || f.includes("games")) return "맵 출전 경험";
  if (f.includes("prior_kd") || f.includes("kd")) return "K/D 비율";
  if (f.includes("role_") && f.includes("count")) return "요원 역할군 카운트";
  if (f.includes("form")) return "팀 최근 폼";
  if (f.includes("balance") || f.includes("role")) return "역할 균형";
  if (f.startsWith("map_")) {
    const m = raw.slice(4);
    return "맵: " + m.charAt(0).toUpperCase() + m.slice(1);
  }
  return raw;
}

// 혼동행렬에서 정확도/정밀도/재현율/F1 도출 (class1 = 팀 A 승 = 양성)
function metricsFromCM(
  cm?: [[number, number], [number, number]],
): { acc: number; prec: number; rec: number; f1: number } | null {
  if (!cm) return null;
  const tn = cm[0][0];
  const fp = cm[0][1];
  const fn = cm[1][0];
  const tp = cm[1][1];
  const tot = tn + fp + fn + tp || 1;
  const acc = (tp + tn) / tot;
  const prec = tp / (tp + fp || 1);
  const rec = tp / (tp + fn || 1);
  const f1 = (2 * prec * rec) / (prec + rec || 1);
  return { acc, prec, rec, f1 };
}

function KdWinrateCard({
  points,
  className = "",
}: {
  points: { kd: number; wr: number }[];
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardTitle sub="이전연도 KD가 높을수록 승률↑">KD ↔ 승률 관계</CardTitle>
      {(() => {
        const W = 248;
        const H = 140;
        const PAD = { t: 12, r: 12, b: 26, l: 34 };
        const kdMin = Math.min(...points.map((p) => p.kd));
        const kdMax = Math.max(...points.map((p) => p.kd));
        const wrMin = Math.min(...points.map((p) => p.wr)) - 0.02;
        const wrMax = Math.max(...points.map((p) => p.wr)) + 0.02;
        const cx = (kd: number) =>
          PAD.l +
          ((kd - kdMin) / (kdMax - kdMin || 1)) * (W - PAD.l - PAD.r);
        const cy = (wr: number) =>
          H -
          PAD.b -
          ((wr - wrMin) / (wrMax - wrMin || 1)) * (H - PAD.t - PAD.b);
        return (
          <div className="overflow-x-auto">
            <svg
              width={W}
              height={H}
              className="w-full"
              style={{ maxHeight: 160 }}
            >
              {[0.25, 0.5, 0.75].map((f) => {
                const y = PAD.t + f * (H - PAD.t - PAD.b);
                return (
                  <line
                    key={f}
                    x1={PAD.l}
                    x2={W - PAD.r}
                    y1={y}
                    y2={y}
                    stroke="rgba(255,255,255,0.08)"
                  />
                );
              })}
              <line
                x1={cx(points[0].kd)}
                y1={cy(points[0].wr)}
                x2={cx(points[points.length - 1].kd)}
                y2={cy(points[points.length - 1].wr)}
                stroke="rgba(41,197,224,0.45)"
                strokeWidth={1.5}
                strokeDasharray="4 3"
              />
              {points.map((p, i) => (
                <circle
                  key={i}
                  cx={cx(p.kd)}
                  cy={cy(p.wr)}
                  r={3.5}
                  fill="var(--color-red)"
                  opacity={0.85}
                />
              ))}
              <text
                x={PAD.l}
                y={H - 4}
                fontSize={9}
                fill="var(--color-muted)"
              >
                KD →
              </text>
              <text
                x={W - PAD.r}
                y={PAD.t + 8}
                textAnchor="end"
                fontSize={9}
                fill="var(--color-muted)"
              >
                승률
              </text>
            </svg>
          </div>
        );
      })()}
    </Card>
  );
}

function AgentSampleCard({
  summaries,
  maxSample,
  className = "",
}: {
  summaries: { agent: string; totalSample: number }[];
  maxSample: number;
  className?: string;
}) {
  const visibleSamples = summaries.slice(0, 6);
  return (
    <Card className={className}>
      <CardTitle sub={`상위 ${visibleSamples.length}명 · 전체 ${summaries.length}요원`}>
        요원 표본 수
      </CardTitle>
      <div className="flex flex-col gap-2">
        {visibleSamples.map((item, idx) => {
          const color = AGENT_META_COLORS[idx % AGENT_META_COLORS.length];
          return (
            <HBar
              key={item.agent}
              label={item.agent}
              value={item.totalSample.toLocaleString()}
              pct={(item.totalSample / maxSample) * 100}
              color={color}
              strong={idx === 0}
            />
          );
        })}
      </div>
    </Card>
  );
}

type AgentMetaSummary = {
  agent: string;
  avgWin: number;
  first?: AgentMetaYear;
  latest?: AgentMetaYear;
  totalSample: number;
  trend: number;
};

function TargetDistCard({
  targetDist,
  trainRows,
  testRows,
}: {
  targetDist: { label: number; count: number }[];
  trainRows?: number;
  testRows?: number;
}) {
  const total = targetDist.reduce((s, d) => s + d.count, 0);
  const aCount = targetDist.find((d) => d.label === 1)?.count ?? 0;
  const bCount = targetDist.find((d) => d.label === 0)?.count ?? 0;
  const aPct = total > 0 ? (aCount / total) * 100 : 0;
  const bPct = total > 0 ? (bCount / total) * 100 : 0;

  return (
    <Card>
      <CardTitle sub="맵 단위 승패 샘플 기준">타겟 분포 · 맵 승패</CardTitle>
      <div className="flex flex-col gap-3">
        <HBar
          label="팀 A 승"
          value={`${aPct.toFixed(0)}%`}
          pct={aPct}
          color="var(--color-red)"
        />
        <HBar
          label="팀 B 승"
          value={`${bPct.toFixed(0)}%`}
          pct={bPct}
          color="var(--color-cyan)"
        />
        <div className="text-xs text-muted">
          Train 샘플{" "}
          <span className="font-bold text-ink tabular-nums">
            {Number(trainRows ?? 0).toLocaleString()}
          </span>{" "}
          · Test 샘플{" "}
          <span className="font-bold text-ink tabular-nums">
            {Number(testRows ?? 0).toLocaleString()}
          </span>
        </div>
      </div>
    </Card>
  );
}

function MapCountsCard({
  rows,
}: {
  rows: { map: string; count: number }[];
}) {
  const top = [...rows].sort((a, b) => b.count - a.count).slice(0, 6);
  const maxCount = Math.max(...top.map((d) => d.count), 1);

  return (
    <Card>
      <CardTitle sub={`상위 ${top.length}개 · 전체 ${rows.length}맵 · 승패 샘플 기준`}>
        맵별 승패 샘플 수
      </CardTitle>
      <div className="flex flex-col gap-2">
        {top.map((d) => (
          <HBar
            key={d.map}
            label={d.map}
            value={d.count.toLocaleString()}
            pct={(d.count / maxCount) * 100}
            color="var(--color-cyan)"
          />
        ))}
      </div>
    </Card>
  );
}

function RoleMetaCompactCard({
  rows,
  years,
  roles,
}: {
  rows: RoleMetaYear[];
  years: number[];
  roles: string[];
}) {
  return (
    <Card>
      <CardTitle
        sub={
          years.length >= 2
            ? `${years[0]} → ${years[years.length - 1]} 역할 비중`
            : "역할 비중 변화"
        }
      >
        연도별 역할 메타
      </CardTitle>
      {(() => {
        const W = 300;
        const H = 132;
        const PAD = { t: 12, r: 12, b: 24, l: 34 };
        if (years.length < 2 || roles.length === 0)
          return <p className="text-xs text-muted">데이터 부족</p>;
        const allRates = rows.map((d) => d.pick_rate);
        const rMin = Math.max(0, Math.min(...allRates) - 0.02);
        const rMax = Math.min(1, Math.max(...allRates) + 0.02);
        const cx = (yi: number) =>
          PAD.l + (yi / (years.length - 1)) * (W - PAD.l - PAD.r);
        const cy = (rate: number) =>
          H -
          PAD.b -
          ((rate - rMin) / (rMax - rMin || 1)) * (H - PAD.t - PAD.b);

        return (
          <div>
            <svg
              viewBox={`0 0 ${W} ${H}`}
              className="h-[132px] w-full"
              role="img"
              aria-label="연도별 역할 메타 선차트"
            >
              {[0.25, 0.5, 0.75].map((f) => {
                const y = PAD.t + f * (H - PAD.t - PAD.b);
                return (
                  <line
                    key={f}
                    x1={PAD.l}
                    x2={W - PAD.r}
                    y1={y}
                    y2={y}
                    stroke="rgba(255,255,255,0.08)"
                  />
                );
              })}
              {years.map((yr, yi) => (
                <text
                  key={yr}
                  x={cx(yi)}
                  y={H - 5}
                  textAnchor="middle"
                  fontSize={9}
                  fill="var(--color-muted)"
                >
                  {yr}
                </text>
              ))}
              {roles.map((role) => {
                const pts = years
                  .map((yr, yi) => {
                    const entry = rows.find(
                      (d) => d.year === yr && d.role === role,
                    );
                    return entry ? { x: cx(yi), y: cy(entry.pick_rate) } : null;
                  })
                  .filter((p): p is { x: number; y: number } => p !== null);
                if (pts.length < 2) return null;
                const d = pts
                  .map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`)
                  .join(" ");
                return (
                  <path
                    key={role}
                    d={d}
                    fill="none"
                    stroke={ROLE_COLOR[role] ?? "gray"}
                    strokeWidth={2.2}
                    strokeLinejoin="round"
                  />
                );
              })}
            </svg>
            <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
              {roles.map((role) => (
                <span key={role} className="flex min-w-0 items-center gap-1.5">
                  <span
                    className="inline-block h-2 w-2 shrink-0 rounded-sm"
                    style={{ background: ROLE_COLOR[role] ?? "gray" }}
                  />
                  <span className="truncate text-muted">
                    {ROLE_SHORT[role] ?? role}
                  </span>
                </span>
              ))}
            </div>
          </div>
        );
      })()}
    </Card>
  );
}

function AgentMetaCompactCard({
  rows,
  years,
  agents,
  totalAgents,
}: {
  rows: AgentMetaYear[];
  years: number[];
  agents: string[];
  totalAgents: number;
}) {
  return (
    <Card>
      <CardTitle sub={`상위 ${agents.length}명 선차트 · 전체 ${totalAgents}요원`}>
        연도별 요원 메타
      </CardTitle>
      {(() => {
        const W = 320;
        const H = 132;
        const PAD = { t: 12, r: 14, b: 24, l: 34 };
        if (years.length < 2 || agents.length === 0)
          return <p className="text-xs text-muted">데이터 부족</p>;
        const selected = rows.filter((d) => agents.includes(d.agent));
        const yMax = Math.min(
          1,
          Math.max(0.05, Math.max(...selected.map((d) => d.pick_rate)) * 1.16),
        );
        const cx = (yi: number) =>
          PAD.l + (yi / (years.length - 1)) * (W - PAD.l - PAD.r);
        const cy = (rate: number) =>
          H - PAD.b - (rate / (yMax || 1)) * (H - PAD.t - PAD.b);
        const entryFor = (agent: string, year: number) =>
          selected.find((d) => d.agent === agent && d.year === year);
        const latestFor = (agent: string) => {
          for (let i = years.length - 1; i >= 0; i -= 1) {
            const hit = entryFor(agent, years[i]);
            if (hit) return hit;
          }
          return undefined;
        };

        return (
          <div>
            <svg
              viewBox={`0 0 ${W} ${H}`}
              className="h-[132px] w-full"
              role="img"
              aria-label="연도별 요원 메타 선차트"
            >
              {[0, 0.5, 1].map((f) => {
                const value = yMax * f;
                const y = cy(value);
                return (
                  <g key={f}>
                    <line
                      x1={PAD.l}
                      x2={W - PAD.r}
                      y1={y}
                      y2={y}
                      stroke="rgba(255,255,255,0.08)"
                    />
                    <text
                      x={PAD.l - 7}
                      y={y + 3}
                      textAnchor="end"
                      fontSize={9}
                      fill="var(--color-muted)"
                    >
                      {(value * 100).toFixed(0)}%
                    </text>
                  </g>
                );
              })}
              {years.map((yr, yi) => (
                <text
                  key={yr}
                  x={cx(yi)}
                  y={H - 5}
                  textAnchor="middle"
                  fontSize={9}
                  fill="var(--color-muted)"
                >
                  {yr}
                </text>
              ))}
              {agents.map((agent, ai) => {
                const pts = years
                  .map((yr, yi) => {
                    const entry = entryFor(agent, yr);
                    return entry
                      ? { x: cx(yi), y: cy(entry.pick_rate), entry }
                      : null;
                  })
                  .filter(
                    (
                      p,
                    ): p is {
                      x: number;
                      y: number;
                      entry: AgentMetaYear;
                    } => p !== null,
                  );
                if (pts.length < 2) return null;
                const d = pts
                  .map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`)
                  .join(" ");
                const color = AGENT_META_COLORS[ai % AGENT_META_COLORS.length];
                return (
                  <g key={agent}>
                    <path
                      d={d}
                      fill="none"
                      stroke={color}
                      strokeWidth={2.2}
                      strokeLinejoin="round"
                    />
                    {pts.map((p) => (
                      <circle
                        key={`${agent}-${p.entry.year}`}
                        cx={p.x}
                        cy={p.y}
                        r={3.2}
                        fill={color}
                      />
                    ))}
                  </g>
                );
              })}
            </svg>
            <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
              {agents.map((agent, ai) => {
                const latest = latestFor(agent);
                const color = AGENT_META_COLORS[ai % AGENT_META_COLORS.length];
                return (
                  <div
                    key={agent}
                    className="flex min-w-0 items-center gap-1.5"
                    title={
                      latest
                        ? `${agent} 최신 픽률 ${(latest.pick_rate * 100).toFixed(1)}%`
                        : agent
                    }
                  >
                    <span
                      className="inline-block h-2 w-2 shrink-0 rounded-sm"
                      style={{ background: color }}
                    />
                    <span className="truncate font-bold text-ink">{agent}</span>
                    {latest && (
                      <span className="shrink-0 tabular-nums text-muted">
                        {(latest.pick_rate * 100).toFixed(1)}%
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })()}
    </Card>
  );
}

function AgentTrendCard({
  summaries,
}: {
  summaries: AgentMetaSummary[];
}) {
  const rows = summaries
    .filter((item) => item.latest)
    .sort((a, b) => b.trend - a.trend)
    .slice(0, 6);
  const maxAbs = Math.max(...rows.map((item) => Math.abs(item.trend)), 0.001);

  return (
    <Card>
      <CardTitle sub="최초 연도 대비 최신 픽률 변화">픽률 상승 요원</CardTitle>
      <div className="flex flex-col gap-2">
        {rows.map((item, idx) => {
          const color =
            item.trend >= 0
              ? AGENT_META_COLORS[idx % AGENT_META_COLORS.length]
              : "var(--color-muted)";
          const trendText = `${item.trend > 0 ? "+" : ""}${(
            item.trend * 100
          ).toFixed(1)}%p`;
          return (
            <HBar
              key={item.agent}
              label={item.agent}
              value={trendText}
              pct={(Math.abs(item.trend) / maxAbs) * 100}
              color={color}
              strong={idx === 0}
            />
          );
        })}
      </div>
    </Card>
  );
}

export default function ModelPage() {
  const [m, setM] = useState<ModelInfo | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getModel()
      .then(setM)
      .catch((e) => setErr((e as Error).message));
  }, []);

  if (err) return <ErrorBanner message={err} />;
  if (!m) return <Spinner label="모델 정보를 불러오는 중…" />;

  // 핵심 지표
  const primaryAuc = m.eval?.primary_auc ?? m.metrics?.test_auc ?? 0;
  const primaryLabel = m.eval?.primary_label ?? "Test AUC";
  const secondaryAuc = m.eval?.secondary_auc ?? m.metrics?.train_auc ?? null;
  const secondaryLabel = m.eval?.secondary_label ?? "Train AUC";

  // 앙상블 모델 / 혼동행렬
  const ensemble: PerModelMetrics | undefined = m.models?.find(
    (md) => md.name === "Ensemble",
  );
  const cmData = ensemble?.confusion_matrix as
    | [[number, number], [number, number]]
    | undefined;
  const cm = metricsFromCM(cmData);

  // 데이터셋 분할 (train/test) — 현재 advanced 맵 단위 승패 샘플 기준
  const targetTotal = m.eda?.target_dist?.reduce((s, d) => s + d.count, 0) ?? 0;
  const tr = m.metrics?.train_rows;
  const te = m.metrics?.test_rows;
  const hasRows =
    typeof tr === "number" && tr > 0 && typeof te === "number" && te > 0;
  const splitTotal = hasRows ? tr + te : targetTotal;
  const splitSlices =
    splitTotal > 0
      ? [
          {
            label: "Train",
            value: hasRows ? tr : Math.round(splitTotal * 0.82),
            color: "var(--color-red)",
          },
          {
            label: "Test",
            value: hasRows ? te : Math.round(splitTotal * 0.18),
            color: "var(--color-cyan)",
          },
        ]
      : [];

  // 모델 비교 (가로 막대) — 베이스라인 참조 + 단일 모델 + 앙상블
  const baselineAuc =
    typeof m.metrics?.baseline_auc === "number"
      ? m.metrics.baseline_auc
      : undefined;
  const cmpRows: { name: string; auc: number; strong: boolean }[] = [
    ...(baselineAuc != null
      ? [{ name: "베이스라인 LR+DT", auc: baselineAuc, strong: false }]
      : []),
    ...(m.models ?? [])
      .filter((md) => md.name !== "Ensemble" && typeof md.test_auc === "number")
      .map((md) => ({
        name: MODEL_KO[md.name] ?? md.name,
        auc: md.test_auc as number,
        strong: false,
      })),
    ...(ensemble && typeof ensemble.test_auc === "number"
      ? [
          {
            name: MODEL_KO.Ensemble,
            auc: ensemble.test_auc,
            strong: true,
          },
        ]
      : []),
  ];

  // 과적합 점검 (train vs test 그룹 막대)
  const overfitRows = (m.models ?? []).map((md) => ({
    name: MODEL_KO[md.name]?.startsWith("앙상블") ? "앙상블" : md.name,
    values: { train: md.train_auc ?? 0, test: md.test_auc ?? 0 },
  }));
  const overfitSeries = [
    { key: "train", color: "var(--color-cyan)", label: "train" },
    { key: "test", color: "var(--color-red)", label: "test" },
  ];

  // 전역 피처 중요도 (상위 7)
  const topFeat = [...m.global_importance]
    .sort((a, b) => b.importance - a.importance)
    .slice(0, 6);
  const maxImp = Math.max(...topFeat.map((g) => g.importance), 1e-9);
  const featureGroups = m.feature_groups ?? [];
  const maxGroupImportance = Math.max(
    ...featureGroups.map((g) => g.importance),
    1e-9,
  );
  const confidenceBins = m.confidence_bins ?? [];

  // EDA
  const eda = m.eda;
  const roleMetaYears = eda?.role_meta_by_year
    ? [...new Set(eda.role_meta_by_year.map((d) => d.year))].sort(
        (a, b) => a - b,
      )
    : [];
  const roleMetaRoles = eda?.role_meta_by_year
    ? [...new Set(eda.role_meta_by_year.map((d) => d.role))]
    : [];
  const agentMeta = eda?.agent_meta_by_year ?? [];
  const agentMetaYears = agentMeta.length
    ? [...new Set(agentMeta.map((d) => d.year))].sort((a, b) => a - b)
    : [];
  const agentSampleTotals = agentMeta.reduce<Record<string, number>>(
    (acc, item) => {
      acc[item.agent] = (acc[item.agent] ?? 0) + item.sample;
      return acc;
    },
    {},
  );
  const agentMetaSummaries = Object.entries(agentSampleTotals)
    .map(([agent, totalSample]) => {
      const rows = agentMeta
        .filter((item) => item.agent === agent)
        .sort((a, b) => a.year - b.year);
      const first = rows[0];
      const latest = rows[rows.length - 1];
      const avgWin =
        totalSample > 0
          ? rows.reduce((sum, row) => sum + row.win_rate * row.sample, 0) /
            totalSample
          : 0;
      return {
        agent,
        avgWin,
        first,
        latest,
        totalSample,
        trend:
          first && latest ? latest.pick_rate - first.pick_rate : 0,
      };
    })
    .sort((a, b) => b.totalSample - a.totalSample);
  const agentMetaAgents = agentMetaSummaries
    .slice(0, 6)
    .map((item) => item.agent);
  const maxAgentSample = Math.max(
    ...agentMetaSummaries.map((item) => item.totalSample),
    1,
  );

  // 4개 지표 타일 (혼동행렬에서 도출, 없으면 metrics)
  const metricTiles = [
    {
      label: "정확도",
      value: cm ? cm.acc : (m.metrics?.test_acc ?? null),
    },
    { label: "정밀도", value: cm ? cm.prec : null },
    { label: "재현율", value: cm ? cm.rec : null },
    {
      label: "F1",
      value: cm ? cm.f1 : (m.metrics?.test_f1 ?? null),
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <PageBackdrop dim={0.62} />
      {/* 1. 배너 ───────────────────────────────────────── */}
      <div className="tactical-card tactical-depth relative overflow-hidden rounded-[var(--radius)] border border-line border-l-[5px] border-l-red bg-panel-2/70 px-5 py-3 shadow-[var(--shadow-card)]">
        <CornerAccent />
        <div className="relative">
          <SectionKicker className="mb-1">MODEL</SectionKicker>
          <div className="flex items-baseline gap-3 flex-wrap">
            <span className="text-3xl sm:text-4xl font-extrabold leading-none text-ink">
              심화 앙상블
            </span>
            <span className="text-sm text-muted">
              RF + XGBoost + LightGBM · Soft Voting ·{" "}
              <span className="font-bold text-ink tabular-nums">
                {m.n_features}
              </span>{" "}
              피처
            </span>
          </div>
        </div>
      </div>

      {/* 2. 히어로 스트립 — TEST AUC · ROC · 평가 · 데이터셋 ── */}
      <Card className="p-5">
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-[170px_minmax(340px,1fr)_minmax(0,1.05fr)_minmax(0,0.9fr)] xl:gap-0">
          {/* TEST AUC */}
          <div className="xl:pr-6">
            <SectionKicker>{primaryLabel}</SectionKicker>
            <div className="font-display text-red leading-none text-6xl mt-2">
              {primaryAuc.toFixed(3)}
            </div>
            <div className="mt-3 text-xs text-muted">
              맵 단위 이진 분류
            </div>
          </div>

          {/* ROC 곡선 */}
          <div className="xl:px-6 xl:border-l xl:border-line">
            <CardTitle>ROC 곡선</CardTitle>
            {m.roc ? (
              <div className="overflow-x-auto">
                <RocCurve
                  fpr={m.roc.fpr}
                  tpr={m.roc.tpr}
                  auc={primaryAuc}
                  width={340}
                  height={230}
                />
              </div>
            ) : (
              <p className="text-xs text-muted">ROC 데이터 없음</p>
            )}
          </div>

          {/* 평가 방식 · 정직 병기 */}
          <div className="xl:px-6 xl:border-l xl:border-line">
            <CardTitle>평가 방식 · 산출물 기준</CardTitle>
            <div className="flex flex-col gap-3">
              <HBar
                label={primaryLabel}
                value={primaryAuc.toFixed(3)}
                pct={aucPct(primaryAuc)}
                color="var(--color-red)"
              />
              {secondaryAuc != null && (
                <HBar
                  label={secondaryLabel}
                  value={secondaryAuc.toFixed(3)}
                  pct={aucPct(secondaryAuc)}
                  color="var(--color-cyan)"
                />
              )}
            </div>
            <p className="mt-3 text-xs leading-relaxed text-muted">
              {m.eval?.note ??
                "현재 웹 표시는 advanced train/test 맵 단위 승패 샘플 기준입니다."}
            </p>
          </div>

          {/* 데이터셋 */}
          <div className="xl:pl-6 xl:border-l xl:border-line">
            <CardTitle>데이터셋 단위</CardTitle>
            {splitSlices.length > 0 ? (
              <>
                <Donut slices={splitSlices} size={96} />
                <div className="mt-3">
                  <div className="font-display text-3xl leading-none text-ink tabular-nums">
                    {splitTotal.toLocaleString()}
                  </div>
                  <div className="mt-1 text-xs font-bold text-muted">
                    맵 단위 승패 샘플
                  </div>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-muted">
                  {m.eda?.sample_unit_note ??
                    "모델 학습·평가 기준은 맵별 승패 샘플입니다."}
                </p>
              </>
            ) : (
              <p className="text-xs text-muted">분할 정보 없음</p>
            )}
          </div>
        </div>
      </Card>

      {/* 3. 모델 비교 · 피처 중요도 · 혼동행렬 ──────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* 모델 비교 · AUC */}
        <Card>
          <CardTitle sub="Soft Voting 앙상블이 단일 모델·베이스라인을 앞섭니다">
            모델 비교 · AUC
          </CardTitle>
          <div className="flex flex-col gap-2.5">
            {cmpRows.map((r) => (
              <HBar
                key={r.name}
                label={r.name}
                value={r.auc.toFixed(3)}
                pct={aucPct(r.auc)}
                color={r.strong ? "var(--color-red)" : "var(--color-cyan)"}
                strong={r.strong}
              />
            ))}
          </div>
        </Card>

        {/* 전역 피처 중요도 */}
        <Card>
          <CardTitle sub="예측에 가장 크게 기여하는 입력">
            전역 피처 중요도
          </CardTitle>
          <div className="flex flex-col gap-2.5">
            {topFeat.map((g) => (
              <div key={g.feature} title={g.feature}>
                <HBar
                  label={featureLabel(g.feature)}
                  value={g.importance.toFixed(3)}
                  pct={(g.importance / maxImp) * 100}
                  color="var(--color-red)"
                />
              </div>
            ))}
          </div>
        </Card>

        {/* 혼동 행렬 · 지표 */}
        <Card>
          <CardTitle>혼동 행렬 · 지표</CardTitle>
          {cmData ? (
            <>
              <div className="flex justify-center overflow-x-auto">
                <ConfusionMatrix matrix={cmData} labels={["B승", "A승"]} />
              </div>
              <div className="mt-3 grid grid-cols-4 gap-2 text-center text-xs">
                {metricTiles.map((t) => (
                  <div key={t.label} className="rounded bg-panel/60 p-2">
                    <div className="text-muted">{t.label}</div>
                    <div className="mt-0.5 font-bold text-ink tabular-nums">
                      {t.value != null ? t.value.toFixed(2) : "-"}
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="text-xs text-muted">혼동행렬 데이터 없음</p>
          )}
        </Card>
      </div>

      {/* 4. 심화 모델 해석 ─────────────────────────────── */}
      {(featureGroups.length > 0 || confidenceBins.length > 0) && (
        <>
          <SectionHeader>심화 모델 해석</SectionHeader>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {featureGroups.length > 0 && (
              <Card>
                <CardTitle sub="179피처를 의미 단위로 묶은 전역 중요도">
                  피처 그룹 중요도
                </CardTitle>
                <div className="flex flex-col gap-3">
                  {featureGroups.map((group, idx) => {
                    const color =
                      FEATURE_GROUP_COLORS[
                        idx % FEATURE_GROUP_COLORS.length
                      ];
                    return (
                      <div key={group.group}>
                        <HBar
                          label={group.label}
                          value={`${(group.share * 100).toFixed(1)}%`}
                          pct={(group.importance / maxGroupImportance) * 100}
                          color={color}
                          strong={idx === 0}
                        />
                        {idx < 3 && group.top_features.length > 0 && (
                          <div className="mt-1.5 truncate pl-2 text-[0.68rem] leading-relaxed text-muted">
                            상위 피처:{" "}
                            {group.top_features
                              .slice(0, 2)
                              .map((f) =>
                                f.label && f.label !== f.feature
                                  ? f.label
                                  : featureLabel(f.feature),
                              )
                              .join(" · ")}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </Card>
            )}

            {confidenceBins.length > 0 && (
              <Card>
                <CardTitle sub="advanced test split에서 예측 확률과 실제 적중률 비교">
                  신뢰도 구간별 적중률
                </CardTitle>
                <div className="flex flex-col gap-3">
                  {confidenceBins.map((bin) => {
                    const gap = bin.accuracy - bin.avg_confidence;
                    const color =
                      gap >= -0.03 ? "var(--color-green)" : "var(--color-red)";
                    return (
                      <div key={bin.bin}>
                        <HBar
                          label={bin.bin}
                          value={`${(bin.accuracy * 100).toFixed(1)}%`}
                          pct={bin.accuracy * 100}
                          color={color}
                          strong={bin.accuracy >= 0.7}
                        />
                        <div className="mt-1 grid grid-cols-3 gap-2 text-[0.68rem] text-muted">
                          <span className="truncate">
                            표본{" "}
                            <b className="text-ink tabular-nums">
                              {bin.count.toLocaleString()}
                            </b>
                          </span>
                          <span className="truncate">
                            평균 신뢰{" "}
                            <b className="text-ink tabular-nums">
                              {(bin.avg_confidence * 100).toFixed(1)}%
                            </b>
                          </span>
                          <span
                            className={`truncate text-right tabular-nums ${
                              gap >= -0.03 ? "text-green" : "text-red"
                            }`}
                          >
                            {gap >= 0 ? "+" : ""}
                            {(gap * 100).toFixed(1)}pt
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <p className="mt-3 border-t border-line/70 pt-3 text-xs leading-relaxed text-muted">
                  막대는 적중률, 보조 수치는 같은 구간의 평균 예측 확률과
                  차이입니다.
                </p>
              </Card>
            )}
          </div>
        </>
      )}

      {/* 5. 일반화 진단 ─────────────────────────────────── */}
      {(overfitRows.length > 0 || (m.validation_summary?.length ?? 0) > 0) && (
        <>
          <SectionHeader>일반화 진단</SectionHeader>
          <Card>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-0">
              {/* 과적합 점검 */}
              {overfitRows.length > 0 && (
                <div className="lg:pr-6">
                  <CardTitle>과적합 점검 · train ↔ test AUC</CardTitle>
                  <div className="overflow-x-auto">
                    <GroupedColumns
                      rows={overfitRows}
                      series={overfitSeries}
                      width={540}
                      height={220}
                      yLabel="AUC"
                    />
                  </div>
                </div>
              )}
              {/* 검증 요약 */}
              {m.validation_summary && m.validation_summary.length > 0 && (
                <div className="lg:pl-6 lg:border-l lg:border-line">
                  <CardTitle sub="reports/advanced/validation.json 기준">
                    심화 모델 검증 요약
                  </CardTitle>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    {m.validation_summary.map((item) => (
                      <div
                        key={item.key}
                        className="rounded-[var(--radius-sm)] border border-line/70 bg-bg-2/40 px-3 py-2"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate text-xs text-muted">
                            {item.label}
                          </span>
                          <span
                            className={`text-xs font-extrabold ${
                              item.passed ? "text-green" : "text-red"
                            }`}
                          >
                            {item.passed ? "PASS" : "CHECK"}
                          </span>
                        </div>
                        <div className="mt-1 text-sm font-extrabold text-ink">
                          {item.value}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Card>
        </>
      )}

      {/* 6. EDA · 데이터 탐색 ───────────────────────────── */}
      {eda && (
        <>
          <SectionHeader>EDA · 데이터 탐색</SectionHeader>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <div className="contents">
              {eda.target_dist && eda.target_dist.length > 0 && (
                <TargetDistCard
                  targetDist={eda.target_dist}
                  trainRows={m.metrics.train_rows}
                  testRows={m.metrics.test_rows}
                />
              )}

              {eda.map_counts && eda.map_counts.length > 0 && (
                <MapCountsCard rows={eda.map_counts} />
              )}

              {agentMetaSummaries.length === 0 &&
                eda.kd_winrate &&
                eda.kd_winrate.length > 0 && (
                  <KdWinrateCard points={eda.kd_winrate} />
                )}
            </div>

            {(Boolean(eda.role_meta_by_year?.length) ||
              agentMeta.length > 0) && (
              <div className="contents">
                <div className="contents">
                  {eda.role_meta_by_year &&
                    eda.role_meta_by_year.length > 0 && (
                      <RoleMetaCompactCard
                        rows={eda.role_meta_by_year}
                        years={roleMetaYears}
                        roles={roleMetaRoles}
                      />
                    )}

                  {agentMetaSummaries.length > 0 && (
                    <AgentSampleCard
                      summaries={agentMetaSummaries}
                      maxSample={maxAgentSample}
                    />
                  )}

                  {agentMetaSummaries.length > 0 && (
                    <AgentTrendCard summaries={agentMetaSummaries} />
                  )}

                </div>

                {agentMeta.length > 0 && (
                  <AgentMetaCompactCard
                    rows={agentMeta}
                    years={agentMetaYears}
                    agents={agentMetaAgents}
                    totalAgents={agentMetaSummaries.length}
                  />
                )}
              </div>
            )}
          </div>
        </>
      )}

      {/* 7. 학습·검증 방법 스트립 ───────────────────────── */}
      <div className="rounded-[var(--radius)] border border-line border-l-[3px] border-l-red bg-panel-2/60 px-5 py-3">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="text-sm font-extrabold text-ink shrink-0">
            학습·검증 방법
          </span>
          <span className="text-xs leading-relaxed text-muted">
            경기 시작 전(prematch) 정보만 사용 · 맵 단위 승패 샘플로 train/test
            분할해 누수 차단 · Test AUC {primaryAuc.toFixed(3)}
            {secondaryAuc != null && <> · Train AUC {secondaryAuc.toFixed(3)}</>} ·
            표본 적은 선수는 이전-연도 리그 평균으로 스무딩.
          </span>
        </div>
      </div>
    </div>
  );
}
