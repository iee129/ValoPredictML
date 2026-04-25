import styles from './HistoryTable.module.css';

function ProbCell({ prob }) {
  const pct = Math.round(prob * 100);
  const cls = pct >= 60 ? styles.probHigh : pct >= 40 ? styles.probMed : styles.probLow;
  return <td className={`${styles.tbody} ${cls}`} style={{ display: 'table-cell', padding: '12px 16px' }}><span className={cls}>{pct}%</span></td>;
}

export default function HistoryTable({ items }) {
  if (!items || items.length === 0) {
    return <div className={styles.empty}>예측 기록이 없습니다.</div>;
  }

  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead className={styles.thead}>
          <tr>
            <th>맵</th>
            <th>팀 A</th>
            <th>팀 B</th>
            <th>팀 A 승률</th>
            <th>예측 시각</th>
          </tr>
        </thead>
        <tbody className={styles.tbody}>
          {items.map((item, i) => {
            const pct = Math.round((item.win_probability ?? 0.5) * 100);
            const probCls = pct >= 60 ? styles.probHigh : pct >= 40 ? styles.probMed : styles.probLow;
            return (
              <tr key={item.id ?? i}>
                <td>{item.map}</td>
                <td>
                  <div className={styles.agents}>
                    {(item.team_a || []).map((a) => (
                      <span key={a} className={styles.agentTag}>{a}</span>
                    ))}
                  </div>
                </td>
                <td>
                  <div className={styles.agents}>
                    {(item.team_b || []).map((a) => (
                      <span key={a} className={styles.agentTag}>{a}</span>
                    ))}
                  </div>
                </td>
                <td><span className={probCls}>{pct}%</span></td>
                <td>{item.created_at ? new Date(item.created_at).toLocaleString('ko-KR') : '-'}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
