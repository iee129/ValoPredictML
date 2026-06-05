import { confidenceLevel, pct } from "@/lib/format";

const TONE = {
  HIGH: "text-green bg-[rgba(48,208,140,0.14)] border border-[rgba(48,208,140,0.4)]",
  MEDIUM: "text-amber bg-amber-soft border border-amber/40",
  LOW: "text-muted bg-white/5 border border-line",
} as const;

export default function ConfidenceBadge({
  confidence,
}: {
  confidence: number;
}) {
  const lvl = confidenceLevel(confidence);
  return (
    <span
      title={`확신도 ${pct(confidence)}`}
      className={`inline-flex items-center gap-2 rounded-[var(--radius-sm)] px-3 py-1.5 text-sm font-extrabold ${TONE[lvl]}`}
    >
      <span className="text-[0.7rem] font-bold uppercase opacity-80">
        신뢰도
      </span>
      <span className="tabular-nums">{lvl}</span>
    </span>
  );
}
