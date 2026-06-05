"use client";

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
} from "recharts";
import type { RoleCounts } from "@/types/api";
import { ROLE_KO } from "@/lib/format";

const ROLES = ["duelist", "initiator", "controller", "sentinel"] as const;

// 색은 토큰 SSOT(globals.css) 참조 — 하드코딩 hex 금지.
// recharts는 SVG fill/stroke로 렌더되므로 CSS 변수(var(...))를 그대로 받아 브라우저가 해석한다.
export default function RoleRadar({ a, b }: { a: RoleCounts; b: RoleCounts }) {
  const data = ROLES.map((r) => ({ role: ROLE_KO[r], A: a[r] ?? 0, B: b[r] ?? 0 }));
  return (
    <ResponsiveContainer width="100%" height={210}>
      <RadarChart data={data} outerRadius="68%">
        <PolarGrid stroke="rgba(255,255,255,0.12)" />
        <PolarAngleAxis
          dataKey="role"
          tick={{ fill: "var(--color-muted)", fontSize: 12 }}
        />
        <Radar
          name="A"
          dataKey="A"
          stroke="var(--color-red)"
          fill="var(--color-red)"
          fillOpacity={0.3}
        />
        <Radar
          name="B"
          dataKey="B"
          stroke="var(--color-cyan)"
          fill="var(--color-cyan)"
          fillOpacity={0.25}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
