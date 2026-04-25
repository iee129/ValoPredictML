import styles from './ConfidenceBadge.module.css';

const LEVELS = {
  high:   { label: '높음', cls: styles.high },
  medium: { label: '보통', cls: styles.medium },
  low:    { label: '낮음', cls: styles.low },
};

export default function ConfidenceBadge({ confidence }) {
  const level = confidence >= 0.75 ? 'high' : confidence >= 0.55 ? 'medium' : 'low';
  const { label, cls } = LEVELS[level];

  return (
    <span className={`${styles.badge} ${cls}`}>
      <span className={styles.dot} style={{ backgroundColor: 'currentColor' }} />
      신뢰도 {label}
    </span>
  );
}
