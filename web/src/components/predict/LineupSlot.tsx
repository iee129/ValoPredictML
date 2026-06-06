import type { Slot, Agent, AgentFit, Role } from "@/types/api";
import AgentAvatar from "@/components/ui/AgentAvatar";
import RoleIcon from "@/components/ui/RoleIcon";
import FitBadge from "./FitBadge";

export default function LineupSlot({
  side,
  index,
  value,
  agents,
  fit,
  playerListId,
  featuredPlayerListId,
  onChange,
}: {
  side: "A" | "B";
  index: number;
  value: Slot;
  agents: Agent[];
  fit?: AgentFit;
  playerListId: string;
  featuredPlayerListId?: string;
  onChange: (patch: Partial<Slot>) => void;
}) {
  const role = agents.find((a) => a.name === value.agent)?.role as
    | Role
    | undefined;
  const activePlayerListId =
    value.player.trim() === "" && featuredPlayerListId
      ? featuredPlayerListId
      : playerListId;

  return (
    <div className="flex h-[40px] items-center gap-2 rounded-[var(--radius-sm)] border border-line bg-bg-2/40 px-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.045)]">
      {/* 원형 아바타 */}
      <AgentAvatar
        agent={value.agent || String(index + 1)}
        side={side}
        size={24}
        circular
      />

      <div className="flex-1 min-w-0 flex flex-col">
        {/* 선수 입력 */}
        <input
          list={activePlayerListId}
          value={value.player}
          onChange={(e) => onChange({ player: e.target.value })}
          placeholder="선수"
          aria-label={`팀 ${side} ${index + 1}번 선수`}
          className="h-[16px] w-full border-none bg-transparent text-[12px] font-bold leading-none text-[#f5f7fb] outline-none placeholder:text-[#9ba3b3]/40"
        />
        {/* 요원 선택 */}
        <select
          value={value.agent}
          onChange={(e) => onChange({ agent: e.target.value })}
          aria-label={`팀 ${side} ${index + 1}번 요원`}
          className="mt-0.5 h-[15px] w-full cursor-pointer border-none bg-transparent text-[10px] leading-none text-[#9ba3b3] outline-none"
        >
          <option value="">요원 선택</option>
          {agents.map((a) => (
            <option key={a.name} value={a.name}>
              {a.name}
            </option>
          ))}
        </select>
      </div>

      {/* 역할 아이콘 */}
      {role && <RoleIcon role={role} size="sm" />}

      {/* 적합 배지 */}
      <FitBadge fit={value.agent ? fit : undefined} />
    </div>
  );
}
