import styles from './MapSelector.module.css';

export default function MapSelector({ maps, value, onChange }) {
  return (
    <div className={styles.wrap}>
      <label className={styles.label}>맵 선택</label>
      <select
        className={styles.select}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {maps.map((map) => (
          <option key={map} value={map}>{map}</option>
        ))}
      </select>
    </div>
  );
}
