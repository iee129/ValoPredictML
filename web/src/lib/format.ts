import type { Role } from "@/types/api";

export const pct = (p: number) => `${(p * 100).toFixed(1)}%`;
export const pct0 = (p: number) => `${Math.round(p * 100)}%`;

export type ConfLevel = "HIGH" | "MEDIUM" | "LOW";
export const confidenceLevel = (c: number): ConfLevel =>
  c >= 0.5 ? "HIGH" : c >= 0.2 ? "MEDIUM" : "LOW";

export const ROLE_KO: Record<Role, string> = {
  duelist: "타격대",
  initiator: "척후대",
  controller: "전략가",
  sentinel: "감시자",
};
export const roleKo = (r: Role) => ROLE_KO[r] ?? r;

export const FIT = {
  fit: { mark: "✓", label: "적합", tone: "fit" },
  ok: { mark: "△", label: "보통", tone: "ok" },
  weak: { mark: "✗", label: "비추천", tone: "weak" },
} as const;

// 요원명 약자 (아바타 디스크 표기용) — 영문 2글자
export const agentAbbr = (name: string) => {
  if (!name) return "?";
  const clean = name.replace(/[^A-Za-z]/g, "");
  return (clean.slice(0, 2) || name.slice(0, 2)).toUpperCase();
};
