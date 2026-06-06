import type { FeatureContribution } from "@/types/api";

// 영향 피처 — importance x value 기반 근사 기여도를 중앙축 기준으로 표시.
// 양수(A 기여)=레드 오른쪽 / 음수(B 기여)=시안 왼쪽. 방향으로 유리한 팀을 표현.
export default function FeatureBar({ items }: { items: FeatureContribution[] }) {
  const top = items.slice(0, 6);
  const max = Math.max(...top.map((f) => Math.abs(f.contribution)), 1e-9);
  return (
    <div className="flex flex-col gap-2">
      {top.map((f) => {
        const w = (Math.abs(f.contribution) / max) * 50; // 반폭(0~50%)
        const toA = f.contribution >= 0;
        return (
          <div key={f.feature} className="text-xs">
            <div className="flex justify-between gap-2">
              <span className="text-muted truncate">{f.label}</span>
              <span className="tabular-nums text-ink shrink-0">
                {f.value.toFixed(2)}
              </span>
            </div>
            <div className="relative mt-1 h-2 rounded bg-white/10">
              {/* 중앙축 */}
              <div className="absolute left-1/2 top-0 h-full w-px bg-white/25" />
              <div
                className={`absolute top-0 h-full rounded ${toA ? "left-1/2 bg-red" : "right-1/2 bg-cyan"}`}
                style={{ width: `${w}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
