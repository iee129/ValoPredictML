import type { BalanceWarning } from "@/types/api";

const TONE: Record<BalanceWarning["severity"], string> = {
  high: "text-[#ffe4e8] border-vred/40 bg-vred/10",
  medium: "text-[#fff1cf] border-vamber/40 bg-vamber/10",
  low: "text-muted border-line bg-white/5",
};

export default function BalanceAlert({
  title,
  warnings,
}: {
  title: string;
  warnings: BalanceWarning[];
}) {
  return (
    <div>
      <div className="text-xs font-bold text-muted mb-1">{title}</div>
      {warnings.length === 0 ? (
        <div className="text-xs font-bold text-vgreen">구성 균형 양호 ✅</div>
      ) : (
        <ul className="flex flex-col gap-1">
          {warnings.map((w) => (
            <li
              key={w.code}
              className={`text-xs font-semibold rounded px-2 py-1 border ${TONE[w.severity]}`}
            >
              ⚠ {w.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
