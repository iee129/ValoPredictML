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

export default function RoleRadar({ a, b }: { a: RoleCounts; b: RoleCounts }) {
  const data = ROLES.map((r) => ({ role: ROLE_KO[r], A: a[r] ?? 0, B: b[r] ?? 0 }));
  return (
    <ResponsiveContainer width="100%" height={210}>
      <RadarChart data={data} outerRadius="68%">
        <PolarGrid stroke="rgba(255,255,255,0.12)" />
        <PolarAngleAxis dataKey="role" tick={{ fill: "#9ba3b3", fontSize: 12 }} />
        <Radar name="A" dataKey="A" stroke="#ff4655" fill="#ff4655" fillOpacity={0.3} />
        <Radar name="B" dataKey="B" stroke="#29c5e0" fill="#29c5e0" fillOpacity={0.25} />
      </RadarChart>
    </ResponsiveContainer>
  );
}
