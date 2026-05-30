import { confidenceLevel, pct } from "@/lib/format";

const TONE = {
  HIGH: "text-vgreen border-vgreen/40 bg-vgreen/10",
  MEDIUM: "text-vamber border-vamber/40 bg-vamber/10",
  LOW: "text-muted border-line bg-white/5",
} as const;

const LABEL = { HIGH: "높음", MEDIUM: "보통", LOW: "낮음" } as const;

export default function ConfidenceBadge({ confidence }: { confidence: number }) {
  const lvl = confidenceLevel(confidence);
  return (
    <div className={`rounded-lg border px-3 py-2 text-right ${TONE[lvl]}`}>
      <div className="text-[0.7rem] font-bold uppercase opacity-80">확신도</div>
      <div className="text-lg font-extrabold tabular-nums">
        {lvl} · {pct(confidence)}
      </div>
      <div className="text-[0.7rem]">{LABEL[lvl]}</div>
    </div>
  );
}
