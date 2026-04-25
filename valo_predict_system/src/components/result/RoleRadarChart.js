'use client';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, Legend, ResponsiveContainer } from 'recharts';
import styles from './RoleRadarChart.module.css';

const ROLE_LABELS = ['타격대', '척후병', '전략가', '감시자'];

export default function RoleRadarChart({ roleCountsA, roleCountsB }) {
  const data = ROLE_LABELS.map((label, i) => ({
    role: label,
    A: roleCountsA[i] ?? 0,
    B: roleCountsB[i] ?? 0,
  }));

  return (
    <div className={styles.wrap}>
      <p className={styles.title}>팀 역할군 비교</p>
      <div className={styles.chart}>
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data}>
            <PolarGrid stroke="var(--color-valo-border)" />
            <PolarAngleAxis dataKey="role" tick={{ fill: 'var(--color-valo-muted)', fontSize: 12 }} />
            <Radar name="팀 A" dataKey="A" stroke="var(--color-valo-red)" fill="var(--color-valo-red)" fillOpacity={0.25} />
            <Radar name="팀 B" dataKey="B" stroke="var(--color-role-initiator)" fill="var(--color-role-initiator)" fillOpacity={0.25} />
            <Legend wrapperStyle={{ color: 'var(--color-valo-muted)', fontSize: '12px' }} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
