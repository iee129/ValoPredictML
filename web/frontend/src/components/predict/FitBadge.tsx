import type { AgentFit } from "@/types/api";
import { FIT } from "@/lib/format";

const TONE = {
  fit: "text-green bg-[rgba(48,208,140,0.16)]", // 적합 = 초록
  ok: "text-[#9ba3b3] bg-[rgba(155,163,179,0.16)]", // 보통 = 회색
  weak: "text-red bg-[rgba(255,70,85,0.16)]", // 비추천 = 빨강
} as const;

export default function FitBadge({ fit }: { fit?: AgentFit }) {
  if (!fit) return null;
  const f = FIT[fit.verdict];
  const tip =
    fit.source === "rule"
      ? `${f.label} · 도메인 룰(표본 부족)`
      : `${f.label} · 픽률 ${fit.pick_rate != null ? Math.round(fit.pick_rate * 100) : "-"}% · 표본 ${fit.sample}`;
  // 색 + 기호 + 텍스트 3중 인코딩(색맹 대응) — 시안 칩 형태.
  return (
    <span
      title={tip}
      aria-label={tip}
      className={`shrink-0 inline-flex items-center gap-1 rounded-[var(--radius-sm)] px-1.5 py-1 text-[0.7rem] font-bold ${TONE[fit.verdict]}`}
    >
      <span aria-hidden>{f.mark}</span>
      <span>{f.label}</span>
    </span>
  );
}
