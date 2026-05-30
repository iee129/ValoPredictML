"use client";

import { useEffect, useState } from "react";
import { getReplayMatches, getReplay } from "@/lib/api";
import type { ReplayMatch, PredictResponse } from "@/types/api";
import ResultPanel from "@/components/result/ResultPanel";
import ReplayOutcome from "@/components/replay/ReplayOutcome";
import ErrorBanner from "@/components/ui/ErrorBanner";
import Spinner from "@/components/ui/Spinner";

export default function ReplayPage() {
  const [matches, setMatches] = useState<ReplayMatch[]>([]);
  const [picked, setPicked] = useState("");
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getReplayMatches(200)
      .then((r) => {
        setMatches(r.items);
        if (r.items[0]) setPicked(r.items[0].match_key);
      })
      .catch((e) => setError((e as Error).message));
  }, []);

  useEffect(() => {
    if (!picked) return;
    setLoading(true);
    setError(null);
    getReplay(picked)
      .then(setResult)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, [picked]);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-extrabold border-l-[3px] border-vred pl-2">
        경기 다시보기
      </h1>

      <div className="rounded-lg border border-line bg-panel2/60 p-4">
        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted font-bold shrink-0">경기 선택</span>
          <select
            className="bg-base2 border border-line rounded-md px-3 py-2 text-sm text-ink flex-1 focus:outline-none focus:border-vred"
            value={picked}
            onChange={(e) => setPicked(e.target.value)}
          >
            {matches.map((m) => (
              <option key={m.match_key} value={m.match_key}>
                {m.label}
              </option>
            ))}
          </select>
        </label>
        {result && (
          <div className="mt-3">
            <ReplayOutcome r={result} />
          </div>
        )}
      </div>

      {error && <ErrorBanner message={error} />}
      {loading && <Spinner label="예측 계산 중…" />}
      {result && <ResultPanel r={result} />}
    </div>
  );
}
