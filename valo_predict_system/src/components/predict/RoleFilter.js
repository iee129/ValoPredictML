import styles from './RoleFilter.module.css';

const ROLES = ['전체', '타격대', '척후병', '전략가', '감시자'];

export default function RoleFilter({ active, onChange }) {
  return (
    <div className={styles.wrap}>
      {ROLES.map((role) => (
        <button
          key={role}
          className={`${styles.btn} ${active === role ? styles.active : ''}`}
          onClick={() => onChange(role)}
        >
          {role}
        </button>
      ))}
    </div>
  );
}
