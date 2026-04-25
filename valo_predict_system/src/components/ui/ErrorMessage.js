import styles from './ErrorMessage.module.css';

export default function ErrorMessage({ message }) {
  if (!message) return null;
  return (
    <div className={styles.box}>
      <span className={styles.icon}>⚠</span>
      <span>{message}</span>
    </div>
  );
}
