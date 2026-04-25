const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export function fetchAgents() {
  return request('/agents');
}

export function fetchMaps() {
  return request('/maps');
}

export function fetchHistory(limit = 20, offset = 0, map = null) {
  const params = new URLSearchParams({ limit, offset });
  if (map) params.set('map', map);
  return request(`/history?${params}`);
}

export function fetchAnalytics() {
  return request('/analytics');
}

export async function predictWinRate(map, teamA, teamB) {
  return request('/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ map, team_a: teamA, team_b: teamB }),
  });
}
