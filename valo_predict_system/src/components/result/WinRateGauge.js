'use client';
import { RadialBarChart, RadialBar, PolarAngleAxis } from 'recharts';
import styles from './WinRateGauge.module.css';

export default function WinRateGauge({ probability }) {
  const pct = Math.round(probability * 100);
  const data = [{ value: pct }];

  const color = pct >= 60
    ? 'var(--color-confidence-high)'
    : pct >= 40
    ? '#f59e0b'
    : '#ef4444';

  return (
    <div className={styles.wrap}>
      <p className={styles.label}>팀 A 예측 승률</p>
      <RadialBarChart
        width={180}
        height={180}
        innerRadius={60}
        outerRadius={85}
        data={data}
        startAngle={90}
        endAngle={-270}
      >
        <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
        <RadialBar
          background={{ fill: 'var(--color-valo-border)' }}
          dataKey="value"
          cornerRadius={6}
          fill={color}
          angleAxisId={0}
        />
        <text x={90} y={85} textAnchor="middle" dominantBaseline="middle" fill={color} fontSize={28} fontWeight={900}>
          {pct}%
        </text>
      </RadialBarChart>
      <p className={styles.sub}>팀 B 예측 승률: {100 - pct}%</p>
    </div>
  );
}
