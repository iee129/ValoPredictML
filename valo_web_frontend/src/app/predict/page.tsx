"use client";

import { useEffect, useMemo, useState } from "react";
import { getOptions, getAgentMapFit, compMatch, predict } from "@/lib/api";
import type {
  Options, Slot, Role, AgentFit, CompMatchResponse, PredictResponse,
} from "@/types/api";
import { balanceCheck } from "@/lib/balance";
import MapSelect from "@/components/predict/MapSelect";
import YearSelect from "@/components/predict/YearSelect";
import TeamLineup from "@/components/predict/TeamLineup";
import Legend from "@/components/insights/Legend";
import MetaMatchBar from "@/components/insights/MetaMatchBar";
import BalanceAlert from "@/components/insights/BalanceAlert";
import ResultPanel from "@/components/result/ResultPanel";
import ErrorBanner from "@/components/ui/ErrorBanner";
import Spinner from "@/components/ui/Spinner";

const five = (): Slot[] => Array.from({ length: 5 }, () => ({ player: "", agent: "" }));

export default function PredictPage() {
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getOptions()
      .then((o) => {
        setOpts(o);
        setMap(o.maps[0]?.name ?? "");
        setYear(o.years[o.years.length - 1] ?? 0);
      })
      .catch((e) => setOptError((e as Error).message));
  }, []);

  // 맵 선택 시 요원-맵 적합도 갱신
  useEffect(() => {
    if (!map) return;
    getAgentMapFit(map)
      .then((r) => setFit(new Map(r.agents.map((a) => [a.name, a]))))
      .catch(() => setFit(new Map()));
  }, [map]);

  const roleOf = useMemo(() => {
    const m = new Map<string, Role>();
    opts?.agents.forEach((a) => m.set(a.name, a.role));
    return m;
  }, [opts]);

  const aAgents = teamA.map((s) => s.agent).filter(Boolean);
  const bAgents = teamB.map((s) => s.agent).filter(Boolean);
  const aKey = aAgents.join("|");
  const bKey = bAgents.join("|");

  // 5요원 완성 시 메타 매칭률 (디바운스)
  useEffect(() => {
    if (!map || aAgents.length !== 5) { setCompA(null); return; }
    const t = setTimeout(() => { compMatch(map, aAgents).then(setCompA).catch(() => setCompA(null)); }, 400);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, aKey]);
  useEffect(() => {
    if (!map || bAgents.length !== 5) { setCompB(null); return; }
    const t = setTimeout(() => { compMatch(map, bAgents).then(setCompB).catch(() => setCompB(null)); }, 400);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, bKey]);

  const balA = balanceCheck(teamA.map((s) => roleOf.get(s.agent)).filter(Boolean) as Role[]);
  const balB = balanceCheck(teamB.map((s) => roleOf.get(s.agent)).filter(Boolean) as Role[]);

  const setSlotA = (i: number, patch: Partial<Slot>) =>
    setTeamA((p) => p.map((s, idx) => (idx === i ? { ...s, ...patch } : s)));
  const setSlotB = (i: number, patch: Partial<Slot>) =>
    setTeamB((p) => p.map((s, idx) => (idx === i ? { ...s, ...patch } : s)));

  function validate(): string | null {
    const all = [...teamA, ...teamB];
    if (all.some((s) => !s.player.trim() || !s.agent))
      return "모든 슬롯에 선수와 요원을 선택하세요.";
    const players = all.map((s) => s.player.trim().toLowerCase());
    if (new Set(players).size !== 10) return "10명의 선수는 서로 달라야 합니다.";
    for (const [name, team] of [["팀 A", teamA], ["팀 B", teamB]] as const) {
      const ag = team.map((s) => s.agent);
      if (new Set(ag).size !== ag.length)
        return `${name} 안에서 같은 요원을 중복할 수 없습니다.`;
    }
    return null;
  }

  async function onPredict() {
    const msg = validate();
    if (msg) { setError(msg); return; }
    setLoading(true);
    setError(null);
    try {
      const res = await predict({ map, cutoff_year: year, team_a: teamA, team_b: teamB });
      setResult(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  if (optError) return <ErrorBanner message={`옵션을 불러오지 못했습니다: ${optError}`} />;
  if (!opts) return <Spinner label="입력 데이터를 불러오는 중…" />;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-4 flex-wrap">
        <MapSelect maps={opts.maps} value={map} onChange={setMap} />
        <YearSelect years={opts.years} value={year} onChange={setYear} />
        <div className="ml-auto">
          <Legend />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] gap-4 items-start">
        {/* 좌 — 라인업 입력 */}
        <div className="rounded-lg border border-line bg-panel2/60 p-4">
          <datalist id="players">
            {opts.players.map((p) => (
              <option key={p} value={p} />
            ))}
          </datalist>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-x-4 gap-y-5">
            <TeamLineup side="A" title="팀 A" slots={teamA} agents={opts.agents} fitByAgent={fit} playerListId="players" onSlot={setSlotA} />
            <TeamLineup side="B" title="팀 B" slots={teamB} agents={opts.agents} fitByAgent={fit} playerListId="players" onSlot={setSlotB} />
          </div>
          <button
            onClick={onPredict}
            disabled={loading}
            className="tactical-cut mt-4 w-full px-8 py-2.5 bg-vred text-white font-extrabold uppercase tracking-wide hover:bg-vred-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "예측 중…" : "승률 예측하기"}
          </button>
          {loading && (
            <Spinner label="이전 연도 기록을 계산 중입니다 (첫 실행은 다소 걸립니다)…" />
          )}
          {error && (
            <div className="mt-3">
              <ErrorBanner message={error} />
            </div>
          )}
        </div>

        {/* 우 — 인사이트 + 예측 결과 */}
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-lg border border-line bg-panel2/60 p-4">
              <div className="text-sm font-bold text-muted mb-2">메타 조합 매칭률</div>
              {compA ? (
                <MetaMatchBar result={compA} side="A" />
              ) : (
                <p className="text-xs text-muted">팀 A 요원 5개를 채우면 표시됩니다.</p>
              )}
              <div className="h-px bg-line my-3" />
              {compB ? (
                <MetaMatchBar result={compB} side="B" />
              ) : (
                <p className="text-xs text-muted">팀 B 요원 5개를 채우면 표시됩니다.</p>
              )}
            </div>
            <div className="rounded-lg border border-line bg-panel2/60 p-4 flex flex-col gap-3">
              <BalanceAlert title="팀 A 구성" warnings={balA} />
              <BalanceAlert title="팀 B 구성" warnings={balB} />
            </div>
          </div>

          {result ? (
            <ResultPanel r={result} />
          ) : (
            <div className="rounded-lg border border-dashed border-line bg-panel2/40 px-6 py-12 text-center">
              <div className="text-lg font-extrabold text-ink mb-1">예측 결과</div>
              <p className="text-sm text-muted leading-relaxed">
                맵·선수·요원을 입력하고{" "}
                <span className="text-vred font-bold">승률 예측하기</span>를 누르면
                <br />이 자리에 승률·신뢰도·역할 구성·근거가 표시됩니다.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
