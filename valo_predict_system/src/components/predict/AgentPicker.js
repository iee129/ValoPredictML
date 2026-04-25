'use client';
import { useState } from 'react';
import AgentCard from './AgentCard';
import RoleFilter from './RoleFilter';
import styles from './AgentPicker.module.css';

const ROLE_MAP = {
  '타격대': 'Duelist',
  '척후병': 'Initiator',
  '전략가': 'Controller',
  '감시자': 'Sentinel',
};

export default function AgentPicker({ agents, selectedTeam, teamLabel, onAgentSelect, onAgentRemove }) {
  const [activeRole, setActiveRole] = useState('전체');

  const filtered = activeRole === '전체'
    ? agents
    : agents.filter((a) => a.role === ROLE_MAP[activeRole]);

  const isSelected = (name) => selectedTeam.includes(name);
  const isDisabled = (name) => !isSelected(name) && selectedTeam.length >= 5;
  const isFull = selectedTeam.length === 5;

  return (
    <div className={styles.section}>
      <div className={styles.header}>
        <span className={styles.teamLabel}>{teamLabel}</span>
        <span className={`${styles.count} ${isFull ? styles.countFull : ''}`}>
          {selectedTeam.length} / 5
        </span>
      </div>
      <RoleFilter active={activeRole} onChange={setActiveRole} />
      <div className={styles.grid}>
        {filtered.map((agent) => (
          <AgentCard
            key={agent.name}
            agent={agent}
            selected={isSelected(agent.name)}
            disabled={isDisabled(agent.name)}
            onClick={() =>
              isSelected(agent.name)
                ? onAgentRemove(agent.name)
                : onAgentSelect(agent.name)
            }
          />
        ))}
      </div>
    </div>
  );
}
