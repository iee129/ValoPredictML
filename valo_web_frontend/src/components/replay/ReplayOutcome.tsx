import type { PredictResponse } from "@/types/api";

export default function ReplayOutcome({ r }: { r: PredictResponse }) {
  const predictedName = r.predicted_winner === "A" ? r.team_a.name : r.team_b.name;
  const actualName = r.actual_winner === "A" ? r.team_a.name : r.team_b.name;
  const hit = r.hit ?? false;
  return (
    <div className="flex items-center gap-4 flex-wrap">
      <div className="text-sm">
        <span className="text-muted">예측 승자</span>{" "}
        <span className="font-extrabold">{predictedName}</span>
      </div>
      <div className="text-sm">
        <span className="text-muted">실제 승자</span>{" "}
        <span className="font-extrabold">{actualName}</span>
      </div>
      <span
        className={`rounded px-3 py-1 text-sm font-extrabold border ${
          hit
            ? "text-vgreen border-vgreen/40 bg-vgreen/10"
            : "text-vred border-vred/40 bg-vred/10"
        }`}
      >
        {hit ? "적중 ✅" : "불일치 ✗"}
      </span>
    </div>
  );
}
