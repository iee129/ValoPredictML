import Link from 'next/link';
import PageWrapper from '@/components/layout/PageWrapper';
import StatCard from '@/components/ui/StatCard';
import styles from './page.module.css';

export const metadata = { title: 'ValoPredictML — 홈' };

export default function HomePage() {
  return (
    <PageWrapper>
      <div className={styles.hero}>
        <h1 className={styles.title}>
          <span className={styles.titleAccent}>VALO</span>PREDICT<span className={styles.titleAccent}>ML</span>
        </h1>
        <p className={styles.subtitle}>
          발로란트 5v5 팀 구성 승률 예측 시스템 — XGBoost + LightGBM 앙상블 모델
        </p>
      </div>

      <div className={styles.grid}>
        <StatCard title="모델 정확도" value="≥80%" desc="XGBoost + LightGBM 앙상블" />
        <StatCard title="지원 맵" value="9개" desc="Ascent, Bind, Haven 외" />
        <StatCard title="에이전트 수" value="24명" desc="전 역할군 커버" />
        <StatCard title="분석 피처" value="15개" desc="역할 분포 · 맵 인코딩 포함" />
      </div>

      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>빠른 시작</h2>
        <div className={styles.quickLinks}>
          <Link href="/predict" className={styles.quickLink}>
            <span className={styles.quickLinkIcon}>🎯</span>
            <span className={styles.quickLinkLabel}>승률 예측</span>
            <span className={styles.quickLinkDesc}>팀 구성을 선택하고 승률을 예측합니다</span>
          </Link>
          <Link href="/history" className={styles.quickLink}>
            <span className={styles.quickLinkIcon}>📋</span>
            <span className={styles.quickLinkLabel}>예측 기록</span>
            <span className={styles.quickLinkDesc}>이전 예측 결과를 조회합니다</span>
          </Link>
          <Link href="/analytics" className={styles.quickLink}>
            <span className={styles.quickLinkIcon}>📊</span>
            <span className={styles.quickLinkLabel}>분석 대시보드</span>
            <span className={styles.quickLinkDesc}>에이전트 · 맵별 통계를 확인합니다</span>
          </Link>
        </div>
      </div>
    </PageWrapper>
  );
}
