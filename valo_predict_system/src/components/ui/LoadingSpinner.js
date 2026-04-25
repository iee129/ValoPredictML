import styles from './LoadingSpinner.module.css';

export default function LoadingSpinner({ size = 'md' }) {
  return (
    <div className={`${styles.wrap} ${size === 'sm' ? styles.sm : ''}`}>
      <div className={styles.spinner} />
    </div>
  );
}
