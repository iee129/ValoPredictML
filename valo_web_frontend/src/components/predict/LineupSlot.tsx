import type { Slot, Agent, AgentFit } from "@/types/api";
import FitBadge from "./FitBadge";

const field =
  "bg-base2 border border-line rounded px-2 py-1.5 text-sm text-ink focus:outline-none focus:border-vred";

export default function LineupSlot({
  side,
  index,
  value,
  agents,
  fit,
  playerListId,
  onChange,
}: {
  side: "A" | "B";
  index: number;
  value: Slot;
  agents: Agent[];
  fit?: AgentFit;
  playerListId: string;
  onChange: (patch: Partial<Slot>) => void;
}) {
  const accent = side === "A" ? "border-l-vred" : "border-l-vcyan";
  const weak = fit?.verdict === "weak";
  return (
    <div className={`flex items-center gap-1.5 border-l-2 ${accent} pl-2`}>
      <span className="text-xs text-muted w-4 shrink-0 text-center">{index + 1}</span>
      <input
        list={playerListId}
        value={value.player}
        onChange={(e) => onChange({ player: e.target.value })}
        placeholder="선수"
        className={`${field} flex-1 min-w-0`}
      />
      <select
        value={value.agent}
        onChange={(e) => onChange({ agent: e.target.value })}
        className={`${field} flex-1 min-w-0 ${weak ? "border-vamber" : ""}`}
      >
        <option value="">요원</option>
        {agents.map((a) => (
          <option key={a.name} value={a.name}>
            {a.name}
          </option>
        ))}
      </select>
      <FitBadge fit={value.agent ? fit : undefined} />
    </div>
  );
}
