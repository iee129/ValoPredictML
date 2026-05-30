import type { Slot, Agent, AgentFit } from "@/types/api";
import LineupSlot from "./LineupSlot";

export default function TeamLineup({
  side,
  title,
  slots,
  agents,
  fitByAgent,
  playerListId,
  onSlot,
}: {
  side: "A" | "B";
  title: string;
  slots: Slot[];
  agents: Agent[];
  fitByAgent: Map<string, AgentFit>;
  playerListId: string;
  onSlot: (index: number, patch: Partial<Slot>) => void;
}) {
  const barColor = side === "A" ? "border-vred" : "border-vcyan";
  return (
    <div>
      <div className={`border-l-[3px] ${barColor} pl-2 mb-2 font-extrabold tracking-wide`}>
        {title}
      </div>
      <div className="flex flex-col gap-1.5">
        {slots.map((s, i) => (
          <LineupSlot
            key={i}
            side={side}
            index={i}
            value={s}
            agents={agents}
            fit={s.agent ? fitByAgent.get(s.agent) : undefined}
            playerListId={playerListId}
            onChange={(patch) => onSlot(i, patch)}
          />
        ))}
      </div>
    </div>
  );
}
