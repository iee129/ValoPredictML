import type { FeatureContribution } from "@/types/api";

export default function FeatureBar({ items }: { items: FeatureContribution[] }) {
  const top = items.slice(0, 6);
  const max = Math.max(...top.map((f) => Math.abs(f.contribution)), 1e-9);
  return (
    <div className="flex flex-col gap-1.5">
      {top.map((f) => {
        const w = (Math.abs(f.contribution) / max) * 100;
        const toA = f.contribution >= 0;
        return (
          <div key={f.feature} className="text-xs">
            <div className="flex justify-between gap-2">
              <span className="text-muted truncate">{f.label}</span>
              <span className="tabular-nums text-ink shrink-0">{f.value.toFixed(2)}</span>
            </div>
            <div className="h-1.5 bg-white/10 rounded mt-0.5">
              <div
                className={`h-full rounded ${toA ? "bg-vred" : "bg-vcyan"}`}
                style={{ width: `${w}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
