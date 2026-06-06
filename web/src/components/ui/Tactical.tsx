import type { ReactNode } from "react";

export function SectionKicker({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`text-[0.7rem] font-extrabold uppercase tracking-[0.18em] text-ink ${className}`}
    >
      <span aria-hidden="true" className="text-red">
        {"//"}
      </span>{" "}
      <span className="text-ink">{children}</span>
    </div>
  );
}

export function CornerAccent({
  tone = "var(--color-red)",
  className = "",
}: {
  tone?: string;
  className?: string;
}) {
  return (
    <span
      aria-hidden="true"
      className={`pointer-events-none absolute right-0 top-0 z-20 h-7 w-7 overflow-hidden ${className}`}
    >
      <span
        className="absolute right-[-8px] top-[8px] block h-[2px] w-[38px] rotate-45"
        style={{ background: tone }}
      />
    </span>
  );
}
