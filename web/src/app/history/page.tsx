"use client";

import { useEffect, useMemo, useState } from "react";
import { getHistory, getHistoryDetail } from "@/lib/api";
import type { HistoryDetailResponse, HistoryItem } from "@/types/api";
import PageBackdrop from "@/components/ui/PageBackdrop";
import ErrorBanner from "@/components/ui/ErrorBanner";
import Spinner from "@/components/ui/Spinner";
import ResultPanel from "@/components/result/ResultPanel";
import { CornerAccent, SectionKicker } from "@/components/ui/Tactical";
import { pct } from "@/lib/format";

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function winnerLabel(item: HistoryItem) {
  return item.predicted_winner === "A" ? item.team_a_name : item.team_b_name;
}

function agentLine(item: HistoryItem) {
  return `${item.team_a_agents.join(" · ")} vs ${item.team_b_agents.join(" · ")}`;
}

function playerLine(item: HistoryItem) {
  return `${item.team_a_players.join(" · ")} vs ${item.team_b_players.join(" · ")}`;
}

function ListRow({
  item,
  active,
  onSelect,
}: {
  item: HistoryItem;
  active: boolean;
  onSelect: (id: string) => void;
}) {
  const aPct = pct(item.team_a_win_probability);
  const bPct = pct(item.team_b_win_probability);
  return (
    <button
      type="button"
      onClick={() => onSelect(item.id)}
      className={`w-full border-b border-line/70 px-3 py-3 text-left transition-colors last:border-b-0 ${
        active ? "bg-red-soft" : "hover:bg-white/[0.04]"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
            <span className="text-sm font-extrabold text-ink">
              {item.map}
            </span>
            <span className="text-xs font-bold text-muted">
              {item.cutoff_year}
            </span>
          </div>
          <div className="mt-1 text-xs font-bold text-red">
            {winnerLabel(item)} 우세
          </div>
        </div>
        <div className="shrink-0 text-right text-xs tabular-nums">
          <div className="font-extrabold text-red">{aPct}</div>
          <div className="font-extrabold text-cyan">{bPct}</div>
        </div>
      </div>
      <div className="mt-2 truncate text-xs text-muted">{agentLine(item)}</div>
      <div className="mt-1 truncate text-[0.68rem] text-muted/80">
        {playerLine(item)}
      </div>
      <div className="mt-2 text-[0.68rem] font-medium text-muted">
        {formatDate(item.created_at)}
      </div>
    </button>
  );
}

function EmptyState() {
  return (
    <div className="tactical-card tactical-depth relative min-h-[420px] overflow-hidden rounded-[var(--radius)] border border-line bg-panel/70 p-6">
      <CornerAccent />
      <SectionKicker>HISTORY</SectionKicker>
      <div className="mt-24 text-center">
        <div className="font-display text-[64px] leading-none text-muted/35">
          0
        </div>
        <p className="mt-3 text-sm font-bold text-ink">
          저장된 예측 히스토리가 없습니다.
        </p>
      </div>
    </div>
  );
}

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<HistoryDetailResponse | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);

  function refresh() {
    setRefreshNonce((value) => value + 1);
  }

  useEffect(() => {
    let alive = true;
    Promise.resolve()
      .then(() => {
        if (!alive) return null;
        setLoadingList(true);
        setError(null);
        return getHistory({ limit: 80 });
      })
      .then((data) => {
        if (!alive || !data) return;
        setItems(data.items);
        setTotal(data.total);
        if (data.items.length === 0) setDetail(null);
        setSelectedId((current) =>
          current && data.items.some((item) => item.id === current)
            ? current
            : (data.items[0]?.id ?? null),
        );
      })
      .catch((e) => {
        if (!alive) return;
        setItems([]);
        setTotal(0);
        setSelectedId(null);
        setDetail(null);
        setError((e as Error).message);
      })
      .finally(() => {
        if (alive) setLoadingList(false);
      });
    return () => {
      alive = false;
    };
  }, [refreshNonce]);

  useEffect(() => {
    if (!selectedId) {
      return;
    }
    let alive = true;
    Promise.resolve()
      .then(() => {
        if (!alive) return null;
        setLoadingDetail(true);
        setError(null);
        return getHistoryDetail(selectedId);
      })
      .then((data) => {
        if (alive && data) setDetail(data);
      })
      .catch((e) => {
        if (alive) {
          setDetail(null);
          setError((e as Error).message);
        }
      })
      .finally(() => {
        if (alive) setLoadingDetail(false);
      });
    return () => {
      alive = false;
    };
  }, [selectedId]);

  const backdropMap = detail?.item.map ?? items[0]?.map ?? "";
  const heroAgent = useMemo(() => {
    const result = detail?.result;
    if (!result) return undefined;
    const lineup = result.lineup ?? detail?.request;
    const slots = result.predicted_winner === "A" ? lineup?.team_a : lineup?.team_b;
    return slots?.find((slot) => slot.agent)?.agent;
  }, [detail]);

  return (
    <div className="flex flex-col gap-4">
      <PageBackdrop map={backdropMap} />
      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[360px_minmax(0,1fr)] lg:gap-6">
        <aside className="tactical-card tactical-depth relative overflow-hidden rounded-[var(--radius)] border border-line bg-panel-2/70 shadow-[var(--shadow-card)]">
          <CornerAccent />
          <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
            <div>
              <SectionKicker>HISTORY</SectionKicker>
              <div className="mt-1 text-xs text-muted">
                {loadingList ? "불러오는 중" : `${total}개 저장됨`}
              </div>
            </div>
            <button
              type="button"
              onClick={refresh}
              disabled={loadingList}
              className="rounded-[var(--radius-sm)] border border-line bg-white/[0.04] px-3 py-1.5 text-xs font-extrabold text-ink transition-colors hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-50"
            >
              새로고침
            </button>
          </div>
          {loadingList ? (
            <div className="p-4">
              <Spinner label="히스토리를 불러오는 중…" />
            </div>
          ) : items.length > 0 ? (
            <div className="max-h-[calc(100vh-150px)] overflow-y-auto">
              {items.map((item) => (
                <ListRow
                  key={item.id}
                  item={item}
                  active={item.id === selectedId}
                  onSelect={setSelectedId}
                />
              ))}
            </div>
          ) : (
            <div className="px-4 py-12 text-center text-sm text-muted">
              저장된 항목 없음
            </div>
          )}
        </aside>

        <section className="min-w-0">
          {error && (
            <div className="mb-4">
              <ErrorBanner message={error} />
            </div>
          )}
          {loadingDetail ? (
            <div className="tactical-card tactical-depth rounded-[var(--radius)] border border-line bg-panel/70 p-6">
              <Spinner label="예측 결과를 불러오는 중…" />
            </div>
          ) : selectedId && detail ? (
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius)] border border-line bg-panel/70 px-4 py-3">
                <div>
                  <div className="text-xs font-bold uppercase tracking-wide text-muted">
                    저장 시각
                  </div>
                  <div className="text-sm font-extrabold text-ink">
                    {formatDate(detail.item.created_at)}
                  </div>
                </div>
                <div className="text-right text-xs font-bold text-muted">
                  {detail.item.map} · {detail.item.cutoff_year}
                </div>
              </div>
              <ResultPanel
                r={detail.result}
                compA={null}
                compB={null}
                heroAgent={heroAgent}
              />
            </div>
          ) : (
            <EmptyState />
          )}
        </section>
      </div>
    </div>
  );
}
