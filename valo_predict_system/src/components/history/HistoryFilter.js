import styles from './HistoryFilter.module.css';

export default function HistoryFilter({ maps, mapFilter, onMapChange }) {
  return (
    <div className={styles.wrap}>
      <span className={styles.label}>맵 필터:</span>
      <select className={styles.select} value={mapFilter} onChange={(e) => onMapChange(e.target.value)}>
        <option value="">전체</option>
        {maps.map((m) => <option key={m} value={m}>{m}</option>)}
      </select>
    </div>
  );
}
