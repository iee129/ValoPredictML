'use client';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import styles from './FeatureImportanceBar.module.css';

export default function FeatureImportanceBar({ featureImportance }) {
  const sorted = [...featureImportance].sort((a, b) => b.importance - a.importance).slice(0, 8);

  return (
    <div className={styles.wrap}>
      <p className={styles.title}>피처 중요도 Top 8</p>
      <div className={styles.chart}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={sorted} layout="vertical" margin={{ left: 8, right: 16 }}>
            <XAxis type="number" tick={{ fill: 'var(--color-valo-muted)', fontSize: 10 }} />
            <YAxis dataKey="feature" type="category" width={110} tick={{ fill: 'var(--color-valo-muted)', fontSize: 10 }} />
            <Tooltip
              contentStyle={{ background: 'var(--color-valo-panel)', border: '1px solid var(--color-valo-border)', borderRadius: '8px', color: 'var(--color-valo-text)' }}
              formatter={(v) => [v.toFixed(4), '중요도']}
            />
            <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
              {sorted.map((_, i) => (
                <Cell key={i} fill={i === 0 ? 'var(--color-valo-red)' : 'var(--color-valo-muted)'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
