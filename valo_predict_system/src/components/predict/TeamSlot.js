import Image from 'next/image';
import { getAgentIconUrl } from '@/lib/agentImage';
import styles from './TeamSlot.module.css';

export default function TeamSlot({ selected, label }) {
  const slots = Array.from({ length: 5 }, (_, i) => selected[i] || null);

  return (
    <div className={styles.wrap}>
      <p className={styles.label}>{label} 선택 현황</p>
      <div className={styles.slots}>
        {slots.map((name, i) => {
          const imgUrl = name ? getAgentIconUrl(name) : null;
          return (
            <div key={i} className={styles.slot}>
              <div className={styles.slotImg}>
                {imgUrl ? (
                  <Image src={imgUrl} alt={name} width={48} height={48} />
                ) : name ? (
                  <span style={{ fontSize: '10px', color: 'var(--color-valo-text)', textAlign: 'center', padding: '2px' }}>{name}</span>
                ) : (
                  <div className={styles.emptySlot}>
                    <span className={styles.emptyIcon}>+</span>
                  </div>
                )}
              </div>
              <span className={styles.slotName}>{name || '—'}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
