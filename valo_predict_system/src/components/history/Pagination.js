import styles from './Pagination.module.css';

export default function Pagination({ page, total, pageSize, onPage }) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className={styles.wrap}>
      <button className={styles.btn} onClick={() => onPage(page - 1)} disabled={page <= 1}>
        ← 이전
      </button>
      <span className={styles.info}>{page} / {totalPages} 페이지</span>
      <button className={styles.btn} onClick={() => onPage(page + 1)} disabled={page >= totalPages}>
        다음 →
      </button>
    </div>
  );
}
