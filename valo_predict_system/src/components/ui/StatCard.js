import styles from './StatCard.module.css';

export default function StatCard({ label, value, sub, accent = '' }) {
  const accentClass = {
    red:   styles.accentRed,
    green: styles.accentGreen,
    amber: styles.accentAmber,
  }[accent] || '';

  return (
    <div className={styles.card}>
      <p className={styles.label}>{label}</p>
      <p className={`${styles.value} ${accentClass}`}>{value}</p>
      {sub && <p className={styles.sub}>{sub}</p>}
    </div>
  );
}
