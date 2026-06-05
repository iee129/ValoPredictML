"use client";

import { useEffect, useState } from "react";
import { getReplayMatches, getReplay } from "@/lib/api";
import type { ReplayMatch, PredictResponse } from "@/types/api";
import PageBackdrop from "@/components/ui/PageBackdrop";
import { mapListIcon } from "@/lib/valorantImages";
import FeatureBar from "@/components/result/FeatureBar";
import ConfidenceBadge from "@/components/result/ConfidenceBadge";
import AgentAvatar from "@/components/ui/AgentAvatar";
import ErrorBanner from "@/components/ui/ErrorBanner";
import Spinner from "@/components/ui/Spinner";
import { CornerAccent, SectionKicker } from "@/components/ui/Tactical";

function CardTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <span
        aria-hidden
        className="inline-block w-[3px] h-[13px] rounded-sm bg-red shrink-0"
      />
      <h3 className="text-sm font-extrabold text-ink leading-none">
        {children}
      </h3>
    </div>
  );
}

function Card({
  children,
  className = "",
  corner = "var(--color-red)",
}: {
  children: React.ReactNode;
  className?: string;
  corner?: string;
}) {
  return (
    <div
      className={`tactical-card tactical-depth relative overflow-hidden rounded-[var(--radius)] border border-line bg-panel-2/60 p-4 shadow-[var(--shadow-card)] ${className}`}
    >
      <CornerAccent tone={corner} />
      {children}
    </div>
  );
}

function Row({
  label,
  value,
  tone = "text-ink",
}: {
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div className="flex items-center justify-between border-b border-line/60 py-2 last:border-0">
      <span className="text-xs text-muted">{label}</span>
      <span className={`text-sm font-extrabold ${tone}`}>{value}</span>
    </div>
  );
}

function ReplayDetail({ r }: { r: PredictResponse }) {
  const hit = r.hit ?? false;
  const winnerIsA = r.predicted_winner === "A";
  const predName = winnerIsA ? r.team_a.name : r.team_b.name;
  const actIsA = r.actual_winner === "A";
  const actName = actIsA ? r.team_a.name : r.team_b.name;
  const winProb = winnerIsA
    ? r.team_a.win_probability
    : r.team_b.win_probability;
  const winPct = Math.round(winProb * 100);
  const loserName = winnerIsA ? r.team_b.name : r.team_a.name;
  const loserPct = 100 - winPct;
  const winTone = winnerIsA ? "text-red" : "text-cyan";
  const winColor = winnerIsA ? "#ff4655" : "#29c5e0";
  const actTone = actIsA ? "text-red" : "text-cyan";
  const actColor = actIsA ? "var(--color-red)" : "var(--color-cyan)";
  const actBorder = actIsA ? "border-l-red" : "border-l-cyan";
  const verdictColor = hit ? "var(--color-green)" : "var(--color-red)";

  return (
    <>
      {/* 판정 + 실제 승자 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div
          className={`tactical-card tactical-depth relative overflow-hidden rounded-[var(--radius)] border border-line bg-panel-2/60 p-5 shadow-[var(--shadow-card)] border-l-[5px] ${
            hit ? "border-l-green" : "border-l-red"
          }`}
        >
          <CornerAccent tone={verdictColor} />
          <CardTitle>판정</CardTitle>
          <div
            className={`text-3xl font-extrabold ${hit ? "text-green" : "text-red"}`}
          >
            {hit ? "예측 적중 ✓" : "예측 빗나감 ✗"}
          </div>
          <div className="mt-2 text-sm text-muted">
            {hit
              ? "모델 예측이 실제 결과와 일치했습니다"
              : "모델 예측이 실제 결과와 달랐습니다"}
          </div>
        </div>

        <Card className={`border-l-[3px] ${actBorder}`} corner={actColor}>
          <CardTitle>실제 승자</CardTitle>
          <div className={`text-4xl font-extrabold leading-none ${actTone}`}>
            {actName}
          </div>
          <div className="mt-4 flex items-center justify-between border-t border-line pt-3">
            <span className="text-xs text-muted">예측 승률</span>
            <span className="font-display text-2xl tabular-nums text-ink">
              {winPct}%
            </span>
          </div>
        </Card>
      </div>

      {/* 모델 예측 · 영향 피처 · 예측 vs 실제 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card corner={winColor}>
          <CardTitle>모델 예측</CardTitle>
          <div className="flex items-center gap-4">
            <div
              className="relative h-[92px] w-[92px] shrink-0 rounded-full"
              style={{
                background: `conic-gradient(${winColor} ${winPct}%, rgba(255,255,255,0.08) 0)`,
              }}
            >
              <div className="absolute inset-[11px] flex items-center justify-center rounded-full bg-panel">
                <span
                  className={`font-display text-2xl tabular-nums ${winTone}`}
                >
                  {winPct}%
                </span>
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <span className={`text-lg font-extrabold ${winTone}`}>
                {predName} 우세
              </span>
              <span className="text-sm text-muted">
                {loserName} {loserPct}%
              </span>
              <div className="mt-1">
                <ConfidenceBadge confidence={r.confidence} />
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <CardTitle>영향 피처</CardTitle>
          <FeatureBar items={r.top_features} />
        </Card>

        <Card>
          <CardTitle>예측 vs 실제</CardTitle>
          <div className="flex flex-col">
            <Row label="예측 승자" value={predName} tone={winTone} />
            <Row label="실제 승자" value={actName} tone={actTone} />
            <Row label="예측 승률" value={`${winPct}%`} />
            <Row
              label="판정"
              value={hit ? "적중 ✓" : "빗나감 ✗"}
              tone={hit ? "text-green" : "text-red"}
            />
          </div>
        </Card>
      </div>

      {/* 경기 조합 · 실제 출전 */}
      <Card>
        <CardTitle>경기 조합 · 실제 출전</CardTitle>
        {r.lineup ? (
          <div className="flex flex-col gap-4">
            {[
              {
                name: r.team_a.name,
                slots: r.lineup.team_a,
                side: "A" as const,
                tone: "text-red",
              },
              {
                name: r.team_b.name,
                slots: r.lineup.team_b,
                side: "B" as const,
                tone: "text-cyan",
              },
            ].map((tm) => (
              <div key={tm.side} className="flex items-center gap-3 flex-wrap">
                <span className={`w-20 shrink-0 font-extrabold ${tm.tone}`}>
                  {tm.name}
                </span>
                <div className="flex gap-2 flex-wrap">
                  {tm.slots.map((s, i) => (
                    <div
                      key={i}
                      className="flex w-[108px] items-center gap-2 rounded-[var(--radius-sm)] border border-line/70 bg-bg-2/45 p-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.045)]"
                    >
                      <AgentAvatar
                        agent={s.agent}
                        side={tm.side}
                        size={34}
                        circular
                      />
                      <span className="min-w-0" title={s.player}>
                        <span
                          className="block truncate text-xs font-extrabold text-ink"
                          aria-label={`선수 ${s.player}`}
                        >
                          {s.player}
                        </span>
                        <span className="block truncate text-[0.68rem] text-muted">
                          {s.agent}
                        </span>
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="rounded-[var(--radius-sm)] border border-dashed border-line/80 bg-bg-2/35 px-4 py-5 text-center text-xs text-muted">
            출전 선수 정보 없음
          </p>
        )}
      </Card>

      {/* 다시보기 설명 */}
      <div className="tactical-card tactical-depth rounded-[var(--radius)] border border-line border-l-[3px] border-l-red bg-panel-2/60 px-5 py-3">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="shrink-0 text-sm font-extrabold text-ink">
            다시보기
          </span>
          <span className="text-xs leading-relaxed text-muted">
            학습에 쓰이지 않은 테스트셋 경기에서 모델의 예측과 실제 결과를
            대조합니다. train/test split 평가의 한계도 함께 확인할 수 있습니다.
          </span>
        </div>
      </div>
    </>
  );
}

// 검색 결과로 노출할 최대 경기 수(전체는 1.6만+ → DOM·성능상 상위 N만 렌더, 나머지는 검색으로 좁힘)
const SEARCH_LIMIT = 300;

export default function ReplayPage() {
  const [q, setQ] = useState("");
  const [matches, setMatches] = useState<ReplayMatch[]>([]);
  const [total, setTotal] = useState(0); // 현재 검색어의 전체 일치 수
  const [totalAll, setTotalAll] = useState<number | null>(null); // 테스트셋 전체 경기 수(검색 안내용)
  const [searching, setSearching] = useState(false);
  const [picked, setPicked] = useState("");
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 검색어 디바운스 → 전체 테스트셋에서 검색. 빈 검색도 첫 목록을 보여줘 시안처럼 기본 선택 상태를 만든다.
  useEffect(() => {
    const needle = q.trim();
    const t = setTimeout(
      () => {
        setSearching(true);
        getReplayMatches({ q: needle, limit: SEARCH_LIMIT })
          .then((r) => {
            setMatches(r.items);
            setTotal(r.total);
            if (!needle) setTotalAll(r.total);
            setPicked((prev) => {
              if (r.items.some((m) => m.match_key === prev)) return prev;
              return r.items[0]?.match_key ?? "";
            });
            if (r.items.length === 0) setResult(null);
          })
          .catch((e) => setError((e as Error).message))
          .finally(() => setSearching(false));
      },
      needle ? 300 : 0,
    );
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    if (!picked) return;
    const controller = new AbortController();
    Promise.resolve()
      .then(() => {
        setLoading(true);
        setError(null);
      })
      .then(() => getReplay(picked))
      .then((r) => {
        if (!controller.signal.aborted) {
          setResult(r);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (!controller.signal.aborted) {
          setError((e as Error).message);
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [picked]);

  const pickedMatch = matches.find((m) => m.match_key === picked) ?? null;

  return (
    <div className="flex flex-col gap-4">
      <PageBackdrop map={pickedMatch?.map} dim={0.62} />

      {/* 헤더 배너 */}
      <div className="tactical-card tactical-depth relative overflow-hidden rounded-[var(--radius)] border border-line border-l-[5px] border-l-red bg-panel-2/70 px-5 py-3 shadow-[var(--shadow-card)]">
        <CornerAccent tone="var(--color-red)" />
        <SectionKicker className="mb-1">REPLAY</SectionKicker>
        <div className="flex items-baseline gap-3 flex-wrap">
          {pickedMatch ? (
            <>
              <span className="text-3xl sm:text-4xl font-extrabold leading-none">
                <span className="text-red">{pickedMatch.team_a}</span>{" "}
                <span className="text-muted text-2xl">vs</span>{" "}
                <span className="text-cyan">{pickedMatch.team_b}</span>
              </span>
              <span className="text-sm text-muted">
                {pickedMatch.map}
                {pickedMatch.date ? ` · ${pickedMatch.date}` : ""}
              </span>
            </>
          ) : (
            <span className="text-3xl font-extrabold text-ink">
              경기 다시보기
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[300px_minmax(0,1fr)] lg:gap-6">
        {/* 좌측: 테스트셋 경기 리스트 (전체) */}
        <aside className="tactical-card tactical-depth min-h-[612px] rounded-[var(--radius)] border border-line bg-panel-2/60 p-3 shadow-[var(--shadow-card)]">
          <div className="mb-3 flex items-center gap-2">
            <span
              aria-hidden
              className="inline-block w-[3px] h-[13px] rounded-sm bg-red shrink-0"
            />
            <h2 className="text-sm font-extrabold text-ink leading-none">
              테스트셋 경기
            </h2>
            <span className="ml-auto text-xs tabular-nums text-muted">
              {q.trim()
                ? total.toLocaleString()
                : (totalAll?.toLocaleString() ?? "—")}
            </span>
          </div>

          {/* 검색창 — 전체 테스트셋에서 팀·맵·날짜·키로 검색 */}
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="팀·맵 검색 (예: T1, Ascent)"
            aria-label="테스트셋 경기 검색"
            className="mb-3 w-full rounded-[6px] border border-white/[0.16] bg-black/40 px-3 h-[34px] text-[13px] text-[#f5f7fb] placeholder:text-muted/70 focus:border-red focus:outline-none"
          />

          {searching && matches.length === 0 ? (
            <Spinner label="검색 중…" />
          ) : matches.length === 0 ? (
            <p className="px-1 py-6 text-center text-xs text-muted">
              일치하는 경기가 없습니다.
            </p>
          ) : (
            <>
              {searching && (
                <div className="mb-2 text-center text-[0.7rem] text-muted">
                  검색 중…
                </div>
              )}
              <div className="flex max-h-[520px] flex-col gap-1.5 overflow-y-auto pr-1">
                {matches.map((m) => {
                  const active = m.match_key === picked;
                  const icon = mapListIcon(m.map);
                  const winnerIsB = m.actual_winner === "B";
                  const activeClass = winnerIsB
                    ? "border-cyan/50 bg-cyan-soft border-l-[3px] border-l-cyan"
                    : "border-red/50 bg-red-soft border-l-[3px] border-l-red";
                  const arrowTone = winnerIsB ? "text-cyan" : "text-red";
                  return (
                    <button
                      key={m.match_key}
                      onClick={() => setPicked(m.match_key)}
                      aria-pressed={active}
                      className={`flex items-center gap-2 rounded-[var(--radius-sm)] border px-2.5 py-2 text-left transition-colors ${
                        active
                          ? activeClass
                          : "border-line bg-bg-2/40 hover:bg-white/[0.06]"
                      }`}
                    >
                      {icon && (
                        <span
                          aria-hidden
                          className="h-8 w-8 shrink-0 rounded bg-cover bg-center opacity-90"
                          style={{ backgroundImage: `url(${icon})` }}
                        />
                      )}
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-bold">
                          <span className="text-red">{m.team_a}</span>
                          <span className="text-muted"> vs </span>
                          <span className="text-cyan">{m.team_b}</span>
                        </span>
                        <span className="block truncate text-xs text-muted">
                          {m.map}
                          {m.date ? ` · ${m.date}` : ""}
                        </span>
                      </span>
                      {active && (
                        <span aria-hidden className={`${arrowTone} text-xs shrink-0`}>
                          ▶
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
              {total > matches.length && (
                <p className="mt-2 px-1 text-center text-[0.7rem] leading-relaxed text-muted">
                  총{" "}
                  <span className="font-bold text-ink tabular-nums">
                    {total.toLocaleString()}
                  </span>
                  개 일치 · 상위 {matches.length}개 표시
                  <br />
                  검색어를 좁혀보세요.
                </p>
              )}
            </>
          )}
        </aside>

        {/* 우측: 시안 replay 상세 */}
        <section className="min-w-0 flex flex-col gap-4">
          {error && <ErrorBanner message={error} />}
          {loading && <Spinner label="예측 계산 중…" />}
          {result && !loading && <ReplayDetail r={result} />}
          {!result && !loading && !error && (
            <div className="rounded-[var(--radius)] border border-dashed border-line bg-panel-2/40 px-6 py-16 text-center">
              <div className="font-display text-5xl text-muted/60 mb-2">VS</div>
              <p className="text-sm text-muted">
                좌측에서{" "}
                <span className="text-red font-bold">테스트셋 경기</span>
                를 선택하면
                <br />
                예측 vs 실제 결과와 근거가 표시됩니다.
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
