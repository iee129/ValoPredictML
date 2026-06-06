import type { Side } from "@/types/api";
import { agentIcon } from "@/lib/valorantImages";

interface Props {
  agent: string;
  side: Side;
  size?: number;
  circular?: boolean;
}

const SIDE_COLOR: Record<Side, string> = {
  A: "var(--color-red)",
  B: "var(--color-cyan)",
};

export default function AgentAvatar({
  agent,
  side,
  size = 36,
  circular = false,
}: Props) {
  const ringColor = SIDE_COLOR[side];
  const icon = agentIcon(agent);
  const initials = agent ? agent.slice(0, 2).toUpperCase() : "??";

  return (
    <span
      className={`inline-flex items-center justify-center overflow-hidden font-extrabold text-ink shrink-0 select-none bg-cover bg-center ${circular ? "rounded-full" : "rounded"}`}
      style={{
        width: size,
        height: size,
        fontSize: size * 0.36,
        background: icon
          ? `var(--color-panel) center/cover no-repeat url(${icon})`
          : "var(--color-panel)",
        outline: `2px solid ${ringColor}`,
        outlineOffset: 1,
      }}
      title={agent || "미선택"}
    >
      {/* 요원 미선택 시 이니셜 폴백 (이미지가 있으면 cover 배경이 덮음) */}
      {!icon && initials}
    </span>
  );
}
