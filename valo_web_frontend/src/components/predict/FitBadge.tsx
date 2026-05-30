import type { AgentFit } from "@/types/api";
import { FIT } from "@/lib/format";

const TONE = {
  fit: "text-vgreen border-vgreen/40 bg-vgreen/10",
  ok: "text-muted border-line bg-white/5",
  weak: "text-vred border-vred/40 bg-vred/10",
} as const;

export default function FitBadge({ fit }: { fit?: AgentFit }) {
  if (!fit) return null;
  const f = FIT[fit.verdict];
  const tip =
    fit.source === "rule"
      ? `${f.label} · 도메인 룰(표본 부족)`
      : `${f.label} · 픽률 ${fit.pick_rate != null ? Math.round(fit.pick_rate * 100) : "-"}% · 표본 ${fit.sample}`;
  // 컴팩트 기호 배지(고정 24×24) — 폭을 거의 차지하지 않아 좁은 칸에서도 안 깨짐. 의미는 범례 참고 + 툴팁.
  return (
    <span
      title={tip}
      aria-label={tip}
      className={`shrink-0 inline-flex items-center justify-center w-6 h-6 rounded border text-xs font-bold ${TONE[fit.verdict]}`}
    >
      {f.mark}
    </span>
  );
}
