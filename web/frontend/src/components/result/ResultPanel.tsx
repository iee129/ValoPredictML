import type {
  PredictResponse,
  CompMatchResponse,
  ModelEval,
} from "@/types/api";
import { pct } from "@/lib/format";
import { agentPortrait } from "@/lib/valorantImages";
import ConfidenceBadge from "./ConfidenceBadge";
import RoleRadar from "./RoleRadar";
import FeatureBar from "./FeatureBar";
import MetaMatchBar from "@/components/insights/MetaMatchBar";
import BalanceAlert from "@/components/insights/BalanceAlert";
import { CornerAccent } from "@/components/ui/Tactical";

function Tile({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="tactical-card tactical-depth flex min-h-[224px] flex-col rounded-[var(--radius)] border border-line bg-panel/70 p-4">
      <div className="text-xs font-bold uppercase tracking-wide text-muted mb-2">
        {title}
      </div>
      <div className="flex-1">{children}</div>
    </div>
  );
}

function confidenceText(confidence: number) {
  const gap = Math.round(confidence * 100);
  const label = confidence >= 0.5 ? "HIGH" : confidence >= 0.2 ? "MEDIUM" : "LOW";
  const rule =
    label === "HIGH"
      ? "50%p 이상"
      : label === "MEDIUM"
        ? "20%p 이상 50%p 미만"
        : "20%p 미만";
  return `신뢰도 ${label}: 두 팀 승률 차이가 ${gap}%p라서 ${rule} 구간입니다. 기준은 HIGH 50%p 이상, MEDIUM 20%p 이상, LOW 20%p 미만입니다.`;
}

export default function ResultPanel({
  r,
  compA,
  compB,
  modelEval,
  heroAgent,
}: {
  r: PredictResponse;
  compA?: CompMatchResponse | null;
  compB?: CompMatchResponse | null;
  modelEval?: ModelEval;
  heroAgent?: string;
}) {
  const aPct = Math.round(r.team_a.win_probability * 100);
  const bPct = 100 - aPct;
  const winnerIsA = r.predicted_winner === "A";
  const winnerName = winnerIsA ? r.team_a.name : r.team_b.name;
  const winPct = winnerIsA ? aPct : bPct;
  const winTone = winnerIsA ? "text-red" : "text-cyan";
  const winGlow = winnerIsA
    ? "drop-shadow-[0_0_24px_rgba(255,70,85,0.45)]"
    : "drop-shadow-[0_0_24px_rgba(41,197,224,0.45)]";
  const primaryAuc = modelEval?.primary_auc;
  const primaryLabel = modelEval?.primary_label ?? "Test AUC";
  const secondaryAuc = modelEval?.secondary_auc;
  const secondaryLabel = modelEval?.secondary_label ?? "Train AUC";

  const reason = r.explanations?.[0]?.text;
  const heroImg = agentPortrait(heroAgent);

  return (
    <div className="flex flex-col gap-4">
      {/* ① 결과 히어로 */}
      <div className="tactical-card tactical-depth relative min-h-[252px] overflow-hidden rounded-[var(--radius)] border border-line bg-panel-2/60 border-l-[5px] border-l-red p-5 shadow-[var(--shadow-card)]">
        <CornerAccent tone={winnerIsA ? "var(--color-red)" : "var(--color-cyan)"} />
        {heroImg && (
          <div
            aria-hidden
            className="hidden lg:block pointer-events-none absolute inset-y-0 right-0 w-[34%] bg-contain bg-right bg-no-repeat opacity-60 [mask-image:linear-gradient(to_left,black_55%,transparent)]"
            style={{ backgroundImage: `url(${heroImg})` }}
          />
        )}
        <div className="relative z-10 flex min-h-[212px] flex-col justify-between lg:pr-[36%]">
          <div className="text-xs font-bold uppercase tracking-wide text-muted">
            예측 승자
          </div>
          <div className="mt-1 flex flex-1 flex-wrap items-center gap-x-6 gap-y-3">
            {/* 거대한 승률 숫자 + 우세 팀 */}
            <div className="flex items-center gap-4">
              <span
                className={`font-display leading-none text-[80px] sm:text-[100px] tabular-nums ${winTone} ${winGlow}`}
              >
                {winPct}%
              </span>
              <div className="flex translate-x-4 flex-col justify-center sm:translate-x-6 lg:translate-x-10">
                <span
                  className={`font-display text-[36px] leading-tight ${winTone}`}
                >
                  {winnerName}
                </span>
                <span className="font-display text-[28px] leading-tight text-[#ece8e1]">
                  우세
                </span>
              </div>
            </div>
            <div className="ml-auto flex flex-col items-end gap-1">
              <ConfidenceBadge confidence={r.confidence} />
              <p className="max-w-[260px] text-right text-[0.68rem] leading-snug text-muted">
                {confidenceText(r.confidence)}
              </p>
              {(primaryAuc != null || secondaryAuc != null) && (
                <div className="flex gap-3 text-[0.68rem] tabular-nums">
                  {primaryAuc != null && (
                    <span className="text-muted">
                      {primaryLabel}{" "}
                      <span className="font-bold text-green">
                        {primaryAuc.toFixed(3)}
                      </span>
                    </span>
                  )}
                  {secondaryAuc != null && (
                    <span className="text-muted">
                      {secondaryLabel}{" "}
                      <span className="font-bold text-amber">
                        {secondaryAuc.toFixed(3)}
                      </span>
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="mt-4">
            <div className="flex flex-wrap justify-between gap-x-2 text-sm font-extrabold">
              <span className="text-red">
                {r.team_a.name} {pct(r.team_a.win_probability)}
              </span>
              <span className="text-cyan">
                {r.team_b.name} {pct(r.team_b.win_probability)}
              </span>
            </div>
            {/* 좌우 모멘텀 바 — 그라디언트 */}
            <div className="flex h-3 rounded-full overflow-hidden mt-1 bg-white/10">
              <div
                style={{
                  width: `${aPct}%`,
                  background: "linear-gradient(to right, #ff5162, #80232b)",
                }}
                className="h-full rounded-[4px]"
              />
              <div
                style={{
                  width: `${bPct}%`,
                  background: "linear-gradient(to right, #2fe3ff, #156370)",
                }}
                className="h-full rounded-[4px]"
              />
            </div>
          </div>
        </div>
      </div>

      {/* ② 큼직한 타일 3개 */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Tile title="영향 피처">
          <FeatureBar items={r.top_features} />
        </Tile>

        <Tile title="역할 구성 · A vs B">
          <RoleRadar a={r.role_counts.team_a} b={r.role_counts.team_b} />
        </Tile>

        <Tile title="조합 점검">
          <div className="flex flex-col gap-3">
            {compA ? (
              <MetaMatchBar result={compA} side="A" />
            ) : (
              <p className="text-xs text-muted">팀 A 메타 매칭률 대기</p>
            )}
            {compB ? (
              <MetaMatchBar result={compB} side="B" />
            ) : (
              <p className="text-xs text-muted">팀 B 메타 매칭률 대기</p>
            )}
            <div className="h-px bg-line" />
            <BalanceAlert title="팀 A 구성" warnings={r.balance.team_a} />
            <BalanceAlert title="팀 B 구성" warnings={r.balance.team_b} />
          </div>
        </Tile>
      </div>

      {/* ③ 한 줄 승부 근거 */}
      {reason && (
        <div className="min-h-[72px] rounded-[var(--radius)] border border-line bg-panel/70 px-4 py-3">
          <div className="text-xs font-bold uppercase tracking-wide text-muted mb-1">
            승부 근거
          </div>
          <p className="text-sm leading-relaxed text-ink">
            <span className="font-extrabold">{winnerName} 우세</span> · {reason}
          </p>
        </div>
      )}
    </div>
  );
}
