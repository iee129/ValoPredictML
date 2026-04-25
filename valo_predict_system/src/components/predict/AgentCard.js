import Image from 'next/image';
import { getAgentIconUrl, ROLE_COLORS } from '@/lib/agentImage';
import styles from './AgentCard.module.css';

export default function AgentCard({ agent, selected, disabled, onClick }) {
  const imgUrl = getAgentIconUrl(agent.name);
  const roleColor = ROLE_COLORS[agent.role] || 'var(--color-valo-muted)';

  const cls = [
    styles.card,
    selected ? styles.selected : '',
    disabled ? styles.disabled : '',
  ].join(' ');

  return (
    <div className={cls} onClick={!disabled ? onClick : undefined}>
      <div className={styles.imgWrap}>
        {imgUrl ? (
          <Image
            src={imgUrl}
            alt={agent.name}
            width={40}
            height={40}
            className={styles.img}
          />
        ) : (
          <span className={styles.fallback}>?</span>
        )}
      </div>
      <span className={styles.name}>{agent.name}</span>
      <span className={styles.roleDot} style={{ backgroundColor: roleColor }} />
      {selected && <span className={styles.checkMark}>✓</span>}
    </div>
  );
}
