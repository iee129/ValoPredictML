import type { CompMatchResponse } from "@/types/api";

export default function MetaMatchBar({
  result,
  side,
}: {
  result: CompMatchResponse;
  side: "A" | "B";
}) {
  const color = side === "A" ? "bg-red" : "bg-cyan";
  const pct = Math.max(0, Math.min(100, result.match_pct));
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-bold text-muted">팀 {side} 메타 매칭률</span>
        <span className="text-xl font-extrabold tabular-nums text-ink">
          {result.match_pct}%
        </span>
      </div>
      <div className="h-2 bg-white/10 rounded-full overflow-hidden mt-1">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-muted mt-1 leading-snug">{result.message}</p>
    </div>
  );
}
