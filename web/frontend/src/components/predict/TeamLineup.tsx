import type { Slot, Agent, AgentFit } from "@/types/api";
import LineupSlot from "./LineupSlot";

export default function TeamLineup({
  side,
  title,
  slots,
  agents,
  fitByAgent,
  playerListId,
  featuredPlayerListId,
  onSlot,
}: {
  side: "A" | "B";
  title: string;
  slots: Slot[];
  agents: Agent[];
  fitByAgent: Map<string, AgentFit>;
  playerListId: string;
  featuredPlayerListId?: string;
  onSlot: (index: number, patch: Partial<Slot>) => void;
}) {
  const barColor = side === "A" ? "border-red" : "border-cyan";
  const textColor = side === "A" ? "text-red" : "text-cyan";
  return (
    <div>
      <div
        className={`mb-1 flex items-center gap-2 border-l-[3px] ${barColor} pl-2`}
      >
        <span className={`font-extrabold tracking-wide ${textColor}`}>
          {title}
        </span>
      </div>
      <div className="flex flex-col gap-0.5">
        {slots.map((s, i) => (
          <LineupSlot
            key={i}
            side={side}
            index={i}
            value={s}
            agents={agents}
            fit={s.agent ? fitByAgent.get(s.agent) : undefined}
            playerListId={playerListId}
            featuredPlayerListId={featuredPlayerListId}
            onChange={(patch) => onSlot(i, patch)}
          />
        ))}
      </div>
    </div>
  );
}
