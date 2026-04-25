'use client';
import { useEffect, useState } from 'react';
import PageWrapper from '@/components/layout/PageWrapper';
import StatCard from '@/components/ui/StatCard';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import ErrorMessage from '@/components/ui/ErrorMessage';
import { fetchAnalytics } from '@/lib/api';
import styles from './page.module.css';

export default function AnalyticsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAnalytics()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageWrapper><LoadingSpinner /></PageWrapper>;
  if (error) return <PageWrapper><ErrorMessage message={error} /></PageWrapper>;

  const topAgents = data?.top_agents ?? [];
  const topMaps = data?.map_stats ?? [];
  const maxAgentCount = topAgents[0]?.count ?? 1;
  const maxMapCount = topMaps[0]?.count ?? 1;

  return (
    <PageWrapper>
      <h1 className={styles.pageTitle}>분석 대시보드</h1>

      <div className={styles.grid}>
        <StatCard title="총 예측 횟수" value={data?.total_predictions ?? '-'} desc="누적 예측 기록" />
        <StatCard title="평균 승률" value={data?.avg_win_probability != null ? `${Math.round(data.avg_win_probability * 100)}%` : '-'} desc="팀 A 기준" />
        <StatCard title="가장 많이 쓴 에이전트" value={topAgents[0]?.name ?? '-'} desc={topAgents[0] ? `${topAgents[0].count}회` : ''} />
        <StatCard title="가장 많이 예측한 맵" value={topMaps[0]?.map ?? '-'} desc={topMaps[0] ? `${topMaps[0].count}회` : ''} />
      </div>

      <div className={styles.charts}>
        <div className={styles.chartCard}>
          <p className={styles.chartTitle}>에이전트 사용 빈도 Top 10</p>
          {topAgents.slice(0, 10).map((a) => (
            <div key={a.name} className={styles.barRow}>
              <span className={styles.barLabel}>{a.name}</span>
              <div className={styles.barTrack}>
                <div className={styles.barFill} style={{ width: `${(a.count / maxAgentCount) * 100}%` }} />
              </div>
              <span className={styles.barValue}>{a.count}</span>
            </div>
          ))}
        </div>

        <div className={styles.chartCard}>
          <p className={styles.chartTitle}>맵별 예측 횟수</p>
          {topMaps.map((m) => (
            <div key={m.map} className={styles.barRow}>
              <span className={styles.barLabel}>{m.map}</span>
              <div className={styles.barTrack}>
                <div className={styles.barFill} style={{ width: `${(m.count / maxMapCount) * 100}%` }} />
              </div>
              <span className={styles.barValue}>{m.count}</span>
            </div>
          ))}
        </div>
      </div>
    </PageWrapper>
  );
}
