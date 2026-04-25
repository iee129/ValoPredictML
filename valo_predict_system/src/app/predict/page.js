'use client';
import { useState, useEffect } from 'react';
import PageWrapper from '@/components/layout/PageWrapper';
import MapSelector from '@/components/predict/MapSelector';
import AgentPicker from '@/components/predict/AgentPicker';
import TeamSlot from '@/components/predict/TeamSlot';
import PredictButton from '@/components/predict/PredictButton';
import WinRateGauge from '@/components/result/WinRateGauge';
import ConfidenceBadge from '@/components/result/ConfidenceBadge';
import RoleRadarChart from '@/components/result/RoleRadarChart';
import FeatureImportanceBar from '@/components/result/FeatureImportanceBar';
import ErrorMessage from '@/components/ui/ErrorMessage';
import { fetchMaps, fetchAgents, predictWinRate } from '@/lib/api';
import styles from './page.module.css';

export default function PredictPage() {
  const [maps, setMaps] = useState([]);
  const [agents, setAgents] = useState([]);
  const [selectedMap, setSelectedMap] = useState('');
  const [teamA, setTeamA] = useState([]);
  const [teamB, setTeamB] = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([fetchMaps(), fetchAgents()]).then(([m, a]) => {
      setMaps(m);
      setSelectedMap(m[0] ?? '');
      setAgents(a);
    });
  }, []);

  const canPredict = selectedMap && teamA.length === 5 && teamB.length === 5;

  async function handlePredict() {
    setLoading(true);
    setError(null);
    try {
      const res = await predictWinRate({ map: selectedMap, team_a: teamA, team_b: teamB });
      setResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const allSelected = [...teamA, ...teamB];

  return (
    <PageWrapper>
      <h1 className={styles.pageTitle}>승률 예측</h1>
      {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

      <div className={styles.layout}>
        <div className={styles.leftPanel}>
          <div className={styles.section}>
            <p className={styles.sectionLabel}>맵</p>
            <MapSelector maps={maps} value={selectedMap} onChange={setSelectedMap} />
          </div>
          <AgentPicker
            agents={agents.filter((a) => !allSelected.includes(a.name) || teamA.includes(a.name))}
            selectedTeam={teamA}
            teamLabel="팀 A"
            onAgentSelect={(n) => setTeamA((p) => [...p, n])}
            onAgentRemove={(n) => setTeamA((p) => p.filter((x) => x !== n))}
          />
        </div>

        <div className={styles.rightPanel}>
          <AgentPicker
            agents={agents.filter((a) => !allSelected.includes(a.name) || teamB.includes(a.name))}
            selectedTeam={teamB}
            teamLabel="팀 B"
            onAgentSelect={(n) => setTeamB((p) => [...p, n])}
            onAgentRemove={(n) => setTeamB((p) => p.filter((x) => x !== n))}
          />
        </div>
      </div>

      <div className={styles.teamSlots}>
        <TeamSlot selected={teamA} label="팀 A" />
        <TeamSlot selected={teamB} label="팀 B" />
      </div>

      <PredictButton onClick={handlePredict} loading={loading} disabled={!canPredict} />

      {result && (
        <div className={styles.resultSection}>
          <div className={styles.resultHeader}>
            <h2 className={styles.resultTitle}>예측 결과</h2>
            <ConfidenceBadge confidence={result.confidence} />
          </div>
          <WinRateGauge probability={result.win_probability} />
          <div className={styles.resultCharts}>
            {result.role_counts && (
              <RoleRadarChart
                roleCountsA={result.role_counts.team_a}
                roleCountsB={result.role_counts.team_b}
              />
            )}
            {result.feature_importance && (
              <FeatureImportanceBar featureImportance={result.feature_importance} />
            )}
          </div>
        </div>
      )}
    </PageWrapper>
  );
}
