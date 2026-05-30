import type { PredictResponse } from "@/types/api";
import { pct } from "@/lib/format";
import ConfidenceBadge from "./ConfidenceBadge";
import RoleRadar from "./RoleRadar";
import FeatureBar from "./FeatureBar";
import ReasonCard from "./ReasonCard";

export default function ResultPanel({ r }: { r: PredictResponse }) {
  const aPct = Math.round(r.team_a.win_probability * 100);
  const bPct = 100 - aPct;
  const winnerName = r.predicted_winner === "A" ? r.team_a.name : r.team_b.name;

  return (
    <div className="tactical-cut rounded-lg border border-line bg-panel2/60 border-l-[5px] border-l-vred p-4 shadow-[0_22px_54px_rgba(0,0,0,0.34)]">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <div className="text-xs font-extrabold text-vred uppercase">예측 승자</div>
          <div className="text-3xl font-extrabold leading-tight">{winnerName}</div>
        </div>
        <ConfidenceBadge confidence={r.confidence} />
      </div>

      <div className="mt-3">
        <div className="flex flex-wrap justify-between gap-x-2 text-sm font-extrabold">
          <span className="text-vred">
            {r.team_a.name} {pct(r.team_a.win_probability)}
          </span>
          <span className="text-vcyan">
            {r.team_b.name} {pct(r.team_b.win_probability)}
          </span>
        </div>
        <div className="flex h-3 rounded-full overflow-hidden mt-1 bg-white/10">
          <div className="bg-vred" style={{ width: `${aPct}%` }} />
          <div className="bg-vcyan" style={{ width: `${bPct}%` }} />
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mt-4">
        <div>
          <div className="text-xs font-bold text-muted mb-1">역할 구성 (A vs B)</div>
          <RoleRadar a={r.role_counts.team_a} b={r.role_counts.team_b} />
        </div>
        <div>
          <div className="text-xs font-bold text-muted mb-1">영향 피처</div>
          <FeatureBar items={r.top_features} />
        </div>
        <ReasonCard winnerName={winnerName} explanations={r.explanations} />
      </div>
    </div>
  );
}
