const AGENT_UUID_MAP = {
  Brimstone:  '95b78ed7-4637-86d9-7e41-71ba8c293152',
  Viper:      '707eab51-4836-f488-046a-cda6bf494859',
  Omen:       '8e253930-4c05-31dd-1b6c-968525494517',
  Killjoy:    '1e58de9c-4950-5125-93e9-a0aee9f98746',
  Cypher:     '117ed9e3-49f3-6512-3ccf-0cada7e3823b',
  Sage:       '569fdd95-4d10-43ab-ca70-79becc718b46',
  Phoenix:    'eb93336a-449b-9c1e-0ac7-dfe9992400f5',
  Sova:       '320b2a48-4d9b-a075-30f1-1f93a9b638fa',
  Jett:       'add6443a-41bd-e414-f6ad-e58d267f4e95',
  Reyna:      'e370fa57-4757-3604-3648-499e1f642d3f',
  Breach:     '5f8d3a7f-467b-97f3-062c-b03c6e87ea35',
  Skye:       '6f2a04ca-43e0-be17-7f36-b3908627744d',
  Yoru:       '7f94d92c-4234-0a36-9646-3a87eb8b5ecc',
  Astra:      '41fb69c1-4189-7b37-f117-bcaf1e96f1bf',
  KAYO:       '601dbbe7-43ce-be57-2a40-4abd24953621',
  Chamber:    '22697a3d-45bf-8dd7-4fec-84a9e28c69d7',
  Neon:       'bb2a4828-46eb-8cd1-e765-15848195d751',
  Fade:       'dade69b4-4f5a-8528-247b-219e5a1facd6',
  Harbor:     '95b78ed7-4637-86d9-7e41-71ba8c293152',
  Gekko:      'e370fa57-4757-3604-3648-499e1f642d3f',
  Deadlock:   'cc8b64c8-4b25-4ff9-6e7f-37b4da43d235',
  Iso:        '0e38b510-41a8-5780-7347-abdb3a1df28a',
  Clove:      '1dbf2edd-4729-0984-3115-daa5eedfd7f5',
  Vyse:       'efba5359-4016-a1e5-7626-b1ae1b6d3399',
};

export function getAgentIconUrl(agentName) {
  const uuid = AGENT_UUID_MAP[agentName];
  if (!uuid) return null;
  return `https://media.valorant-api.com/agents/${uuid}/displayicon.png`;
}

export const ROLE_COLORS = {
  Duelist:    'var(--color-role-duelist)',
  Initiator:  'var(--color-role-initiator)',
  Controller: 'var(--color-role-controller)',
  Sentinel:   'var(--color-role-sentinel)',
};

export const ROLE_LABELS_KR = {
  Duelist:    '타격대',
  Initiator:  '척후병',
  Controller: '전략가',
  Sentinel:   '감시자',
};
