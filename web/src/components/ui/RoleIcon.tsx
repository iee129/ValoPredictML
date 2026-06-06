import type { Role } from "@/types/api";

const ROLE_COLOR: Record<Role, string> = {
  duelist: "var(--color-valo-duelist)",
  initiator: "var(--color-valo-initiator)",
  controller: "var(--color-valo-controller)",
  sentinel: "var(--color-valo-sentinel)",
};

const ROLE_KO: Record<Role, string> = {
  duelist: "타격대",
  initiator: "척후대",
  controller: "전략가",
  sentinel: "감시자",
};

interface Props {
  role: Role;
  showLabel?: boolean;
  size?: "sm" | "md";
}

export default function RoleIcon({
  role,
  showLabel = false,
  size = "sm",
}: Props) {
  const color = ROLE_COLOR[role];
  const dotSize = size === "sm" ? "w-2 h-2" : "w-3 h-3";
  return (
    <span className="inline-flex items-center gap-1">
      <span
        className={`inline-block rounded-full ${dotSize} shrink-0`}
        style={{ backgroundColor: color }}
      />
      {showLabel && (
        <span className="text-xs font-bold" style={{ color }}>
          {ROLE_KO[role]}
        </span>
      )}
    </span>
  );
}
