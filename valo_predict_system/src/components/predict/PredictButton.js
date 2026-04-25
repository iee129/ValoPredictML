import styles from './PredictButton.module.css';

export default function PredictButton({ onClick, loading, disabled }) {
  return (
    <button
      className={styles.btn}
      onClick={onClick}
      disabled={disabled || loading}
    >
      {loading ? (
        <span className={styles.loading}>
          <span className={styles.spinner} />
          예측 중...
        </span>
      ) : (
        '승률 예측하기'
      )}
    </button>
  );
}
