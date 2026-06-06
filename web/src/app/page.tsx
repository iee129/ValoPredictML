"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getOptions,
  getAgentMapFit,
  compMatch,
  predict,
  getModel,
} from "@/lib/api";
import type {
  Options,
  Slot,
  PredictRequest,
  AgentFit,
  CompMatchResponse,
  PredictResponse,
  ModelEval,
} from "@/types/api";
import MapBanner from "@/components/predict/MapBanner";
import PageBackdrop from "@/components/ui/PageBackdrop";
import TeamLineup from "@/components/predict/TeamLineup";
import ResultPanel from "@/components/result/ResultPanel";
import ErrorBanner from "@/components/ui/ErrorBanner";
import Spinner from "@/components/ui/Spinner";
import { CornerAccent, SectionKicker } from "@/components/ui/Tactical";
import { FIT, ROLE_KO } from "@/lib/format";

const ROLE_LEGEND = [
  ["duelist", "var(--color-valo-duelist)"],
  ["initiator", "var(--color-valo-initiator)"],
  ["controller", "var(--color-valo-controller)"],
  ["sentinel", "var(--color-valo-sentinel)"],
] as const;

function PredictLegend() {
  return (
    <div className="rounded-[var(--radius-sm)] border border-line/70 bg-bg-2/35 px-3 py-2 text-[0.68rem] leading-tight text-muted">
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {(["fit", "ok", "weak"] as const).map((key) => (
          <span key={key} className="inline-flex items-center gap-1">
            <span className="font-extrabold text-ink">{FIT[key].mark}</span>
            <span>{FIT[key].label}</span>
          </span>
        ))}
      </div>
      <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1">
        {ROLE_LEGEND.map(([role, color]) => (
          <span key={role} className="inline-flex items-center gap-1">
            <span
              aria-hidden
              className="h-2 w-2 rounded-full"
              style={{ background: color }}
            />
            <span>{ROLE_KO[role]}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

const five = (): Slot[] =>
  Array.from({ length: 5 }, () => ({ player: "", agent: "" }));

const normalizeSlots = (slots: Slot[]) =>
  slots.map((slot) => ({
    player: slot.player.trim(),
    agent: slot.agent,
  }));

const playerKey = (player: string) => player.trim().toLowerCase();

const canonicalizeSlots = (
  slots: Slot[],
  playerLookup: Map<string, string>,
) =>
  slots.map((slot) => {
    const player = slot.player.trim();
    return {
      player: playerLookup.get(playerKey(player)) ?? player,
      agent: slot.agent,
    };
  });

function PredictEmptyPanel({
  readySlots,
  totalSlots,
}: {
  readySlots: number;
  totalSlots: number;
}) {
  const pct = Math.round((readySlots / totalSlots) * 100);
  return (
    <div className="flex flex-col gap-4">
      <div className="tactical-card tactical-depth relative min-h-[252px] overflow-hidden rounded-[var(--radius)] border border-line border-l-[5px] border-l-red bg-panel-2/60 p-5 shadow-[var(--shadow-card)]">
        <div className="absolute inset-y-0 right-0 hidden w-[38%] bg-[radial-gradient(circle_at_center,rgba(255,70,85,0.22),transparent_60%)] lg:block" />
        <div className="relative z-10 flex min-h-[212px] flex-col justify-between">
          <div>
            <div className="text-xs font-bold uppercase tracking-wide text-muted">
              예측 준비
            </div>
            <div className="mt-4 flex flex-wrap items-end gap-x-6 gap-y-3">
              <span className="font-display text-[88px] leading-none text-muted/45 sm:text-[108px]">
                VS
              </span>
              <div className="pb-3">
                <div className="text-3xl font-extrabold text-ink">
                  라인업 입력 대기
                </div>
                <p className="mt-2 max-w-[460px] text-sm leading-relaxed text-muted">
                  맵, 기준연도, 양 팀 선수와 요원을 모두 채우면 같은 영역에서
                  승률과 근거가 바로 표시됩니다.
                </p>
                <p className="mt-2 max-w-[460px] text-xs leading-relaxed text-muted">
                  신뢰도는 두 팀 승률 차이로 계산합니다. HIGH 50%p 이상,
                  MEDIUM 20%p 이상, LOW 20%p 미만 기준입니다.
                </p>
              </div>
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between text-xs font-bold text-muted">
              <span>입력 완료</span>
              <span className="tabular-nums text-ink">
                {readySlots}/{totalSlots}
              </span>
            </div>
            <div className="mt-2 h-3 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-[4px] bg-red"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {[
          ["영향 피처", "예측 후 상위 기여 피처 표시"],
          ["역할 구성", "양 팀 역할군 균형 비교"],
          ["조합 점검", "맵 메타와 구성 적합도 확인"],
        ].map(([title, body]) => (
          <div
            key={title}
            className="tactical-card tactical-depth min-h-[224px] rounded-[var(--radius)] border border-line bg-panel/65 p-4"
          >
            <div className="mb-3 text-xs font-bold uppercase tracking-wide text-muted">
              {title}
            </div>
            <div className="flex h-[150px] items-center justify-center rounded-[var(--radius-sm)] border border-dashed border-line/80 bg-bg-2/35 px-4 text-center text-xs leading-relaxed text-muted">
              {body}
            </div>
          </div>
        ))}
      </div>

      <div className="tactical-card tactical-depth min-h-[72px] rounded-[var(--radius)] border border-line bg-panel/70 px-4 py-3">
        <div className="mb-1 text-xs font-bold uppercase tracking-wide text-muted">
          승부 근거
        </div>
        <p className="text-sm leading-relaxed text-muted">
          실제 모델 응답을 받은 뒤 예측 근거 문장이 이 위치에 표시됩니다.
        </p>
      </div>
    </div>
  );
}

export default function HomePage() {
  const lastResultKey = useRef<string | null>(null);
  const requestSeq = useRef(0);
  const [opts, setOpts] = useState<Options | null>(null);
  const [optError, setOptError] = useState<string | null>(null);
  const [map, setMap] = useState("");
  const [year, setYear] = useState(0);
  const [teamA, setTeamA] = useState<Slot[]>(five());
  const [teamB, setTeamB] = useState<Slot[]>(five());
  const [fit, setFit] = useState<Map<string, AgentFit>>(new Map());
  const [compA, setCompA] = useState<CompMatchResponse | null>(null);
  const [compB, setCompB] = useState<CompMatchResponse | null>(null);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [modelEval, setModelEval] = useState<ModelEval | undefined>();
  const [loading, setLoading] = useState(false);
  const [autoRefreshing, setAutoRefreshing] = useState(false);
  const [autoArmed, setAutoArmed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getOptions()
      .then((o) => {
        setOpts(o);
        setMap(o.maps[0]?.name ?? "");
        setYear(o.years[o.years.length - 1] ?? 0);
      })
      .catch((e) => setOptError((e as Error).message));
    getModel()
      .then((m) => setModelEval(m.eval))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!map) return;
    getAgentMapFit(map)
      .then((r) => setFit(new Map(r.agents.map((a) => [a.name, a]))))
      .catch(() => setFit(new Map()));
  }, [map]);

  const aAgents = teamA.map((s) => s.agent).filter(Boolean);
  const bAgents = teamB.map((s) => s.agent).filter(Boolean);
  const aKey = aAgents.join("|");
  const bKey = bAgents.join("|");

  useEffect(() => {
    const t = setTimeout(() => {
      if (!map || aAgents.length !== 5) {
        setCompA(null);
        return;
      }
      compMatch(map, aAgents)
        .then(setCompA)
        .catch(() => setCompA(null));
    }, 400);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, aKey]);
  useEffect(() => {
    const t = setTimeout(() => {
      if (!map || bAgents.length !== 5) {
        setCompB(null);
        return;
      }
      compMatch(map, bAgents)
        .then(setCompB)
        .catch(() => setCompB(null));
    }, 400);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, bKey]);

  const setSlotA = (i: number, patch: Partial<Slot>) =>
    setTeamA((p) => p.map((s, idx) => (idx === i ? { ...s, ...patch } : s)));
  const setSlotB = (i: number, patch: Partial<Slot>) =>
    setTeamB((p) => p.map((s, idx) => (idx === i ? { ...s, ...patch } : s)));

  const playerLookup = useMemo(() => {
    const lookup = new Map<string, string>();
    for (const player of opts?.players ?? []) {
      lookup.set(playerKey(player), player);
    }
    return lookup;
  }, [opts]);

  const rawPayload = useMemo<PredictRequest>(
    () => ({
      map,
      cutoff_year: year,
      team_a: normalizeSlots(teamA),
      team_b: normalizeSlots(teamB),
    }),
    [map, teamA, teamB, year],
  );
  const payload = useMemo<PredictRequest>(
    () => ({
      ...rawPayload,
      team_a: canonicalizeSlots(rawPayload.team_a, playerLookup),
      team_b: canonicalizeSlots(rawPayload.team_b, playerLookup),
    }),
    [playerLookup, rawPayload],
  );
  const requestKey = useMemo(() => JSON.stringify(payload), [payload]);

  const validatePayload = useCallback(
    (body: PredictRequest): string | null => {
      if (!body.map || !body.cutoff_year) return "맵과 기준연도를 선택하세요.";
      const all = [...body.team_a, ...body.team_b];
      if (all.some((s) => !s.player.trim() || !s.agent))
        return "모든 슬롯에 선수와 요원을 선택하세요.";
      for (const slot of all) {
        if (!playerLookup.has(playerKey(slot.player))) {
          return "선수명은 목록에 있는 전체 이름으로 선택하세요.";
        }
      }
      const players = all.map((s) => playerKey(s.player));
      if (new Set(players).size !== 10)
        return "10명의 선수는 서로 달라야 합니다.";
      for (const [name, team] of [
        ["팀 A", body.team_a],
        ["팀 B", body.team_b],
      ] as const) {
        const ag = team.map((s) => s.agent);
        if (new Set(ag).size !== ag.length)
          return `${name} 안에서 같은 요원을 중복할 수 없습니다.`;
      }
      return null;
    },
    [playerLookup],
  );

  const runPredict = useCallback(
    async (body: PredictRequest, key: string, automatic = false) => {
      const msg = validatePayload(body);
      if (msg) {
        setError(msg);
        if (automatic) setResult(null);
        return;
      }
      const seq = ++requestSeq.current;
      if (automatic) {
        setAutoRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);
      try {
        const res = await predict(body);
        if (seq !== requestSeq.current) return;
        setResult(res);
        lastResultKey.current = key;
        setAutoArmed(true);
      } catch (e) {
        if (seq !== requestSeq.current) return;
        setError((e as Error).message);
        if (automatic) setResult(null);
      } finally {
        if (seq === requestSeq.current) {
          if (automatic) setAutoRefreshing(false);
          else setLoading(false);
        }
      }
    },
    [validatePayload],
  );

  function onPredict() {
    void runPredict(payload, requestKey, false);
  }

  useEffect(() => {
    if (!autoArmed) return;
    const msg = validatePayload(payload);
    if (msg) {
      const timer = setTimeout(() => {
        requestSeq.current += 1;
        setAutoRefreshing(false);
        setError(msg);
        setResult(null);
      }, 0);
      return () => clearTimeout(timer);
    }
    if (requestKey === lastResultKey.current) return;
    const timer = setTimeout(() => {
      void runPredict(payload, requestKey, true);
    }, 650);
    return () => {
      clearTimeout(timer);
      requestSeq.current += 1;
    };
  }, [autoArmed, payload, requestKey, runPredict, validatePayload]);

  if (optError)
    return <ErrorBanner message={`옵션을 불러오지 못했습니다: ${optError}`} />;
  if (!opts) return <Spinner label="입력 데이터를 불러오는 중…" />;

  const mapKo = opts.maps.find((m) => m.name === map)?.ko ?? "";

  // 예측 승자 팀의 대표 요원(듀얼리스트 우선) — 결과 히어로 아트
  const winSlots = result?.predicted_winner === "A" ? teamA : teamB;
  const heroAgent = result
    ? (winSlots.find(
        (s) =>
          s.agent &&
          opts.agents.find((a) => a.name === s.agent)?.role === "duelist",
      )?.agent ?? winSlots.find((s) => s.agent)?.agent)
    : undefined;

  const readySlots = [...teamA, ...teamB].filter(
    (s) => s.player.trim() && s.agent,
  ).length;
  const featuredPlayers =
    opts.featured_players && opts.featured_players.length > 0
      ? opts.featured_players
      : opts.players.slice(0, 80);

  return (
    <div className="flex flex-col gap-4">
      <PageBackdrop map={map} />
      <MapBanner
        map={map}
        ko={mapKo}
        year={year}
        maps={opts.maps}
        years={opts.years}
        onMapChange={setMap}
        onYearChange={setYear}
      />

      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[344px_minmax(0,1fr)] lg:gap-6">
        <aside className="tactical-card tactical-depth relative min-h-[612px] overflow-hidden rounded-[var(--radius)] border border-line bg-panel-2/60 p-4 shadow-[var(--shadow-card)]">
          <CornerAccent />
          <SectionKicker className="mb-3">MATCHUP · 양 팀 라인업</SectionKicker>
          <datalist id="players-featured">
            {featuredPlayers.map((p) => (
              <option key={p} value={p} />
            ))}
          </datalist>
          <datalist id="players-all">
            {opts.players.map((p) => (
              <option key={p} value={p} />
            ))}
          </datalist>
          <div className="flex flex-col gap-4">
            <TeamLineup
              side="A"
              title="팀 A"
              slots={teamA}
              agents={opts.agents}
              fitByAgent={fit}
              playerListId="players-all"
              featuredPlayerListId="players-featured"
              onSlot={setSlotA}
            />
            <TeamLineup
              side="B"
              title="팀 B"
              slots={teamB}
              agents={opts.agents}
              fitByAgent={fit}
              playerListId="players-all"
              featuredPlayerListId="players-featured"
              onSlot={setSlotB}
            />
          </div>
          <div className="mt-3">
            <PredictLegend />
          </div>
          <button
            onClick={onPredict}
            disabled={loading || autoRefreshing}
            className="tactical-cut mt-3 w-full bg-red px-8 py-2 font-extrabold uppercase tracking-wide text-white shadow-[0_0_24px_rgba(255,70,85,0.4)] transition-colors hover:bg-red-dark disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
          >
            {loading ? "예측 중…" : autoRefreshing ? "업데이트 중…" : "승률 예측"}
          </button>
          {(loading || autoRefreshing) && (
            <Spinner
              label={
                autoRefreshing
                  ? "입력 변경을 반영해 새 예측을 계산 중입니다…"
                  : "이전 연도 기록을 계산 중입니다 (첫 실행은 다소 걸립니다)…"
              }
            />
          )}
          {error && (
            <div className="mt-3">
              <ErrorBanner message={error} />
            </div>
          )}
        </aside>

        <section className="min-w-0">
          {result ? (
            <div className="flex flex-col gap-3">
              <ResultPanel
                r={result}
                compA={compA}
                compB={compB}
                modelEval={modelEval}
                heroAgent={heroAgent}
              />
              {result.history_id && (
                <div className="flex justify-end">
                  <Link
                    href="/history"
                    className="rounded-[var(--radius-sm)] border border-line bg-white/[0.04] px-3 py-1.5 text-xs font-extrabold text-ink transition-colors hover:bg-white/[0.08]"
                  >
                    히스토리에 저장됨
                  </Link>
                </div>
              )}
            </div>
          ) : (
            <PredictEmptyPanel readySlots={readySlots} totalSlots={10} />
          )}
        </section>
      </div>
    </div>
  );
}
