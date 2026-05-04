> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 03. lib 모듈 상세

`src/lib/` 폴더에는 API 통신과 이미지 URL 유틸리티 2개 모듈이 있다.

---

## api.js

**위치:** `src/lib/api.js`

### 역할

FastAPI 백엔드와의 모든 HTTP 통신을 중앙화. 모든 page.js는 이 파일을 통해서만 API를 호출한다.

### 기본 URL 설정

```js
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

- 개발 환경: `http://localhost:8000`
- 프로덕션: Vercel 환경변수 `NEXT_PUBLIC_API_URL`에서 주입

### 공통 fetch 래퍼

```js
async function apiFetch(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API Error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
```

### 함수 목록

| 함수 | HTTP | 경로 | 설명 |
|---|---|---|---|
| `predictWinRate(body)` | POST | `/predict` | 승률 예측 |
| `fetchAgents()` | GET | `/agents` | 요원 목록 |
| `fetchMaps()` | GET | `/maps` | 맵 목록 |
| `fetchHistory(params)` | GET | `/history` | 예측 기록 |
| `fetchAnalytics()` | GET | `/analytics` | 통계 집계 |

### predictWinRate

```js
export async function predictWinRate({ teamA, teamB, map }) {
  return apiFetch('/predict', {
    method: 'POST',
    body: JSON.stringify({ team_a: teamA, team_b: teamB, map }),
  });
}
```

### fetchHistory

쿼리스트링 파라미터 지원:
```js
export async function fetchHistory({ page = 1, pageSize = 20, map = '', startDate = '', endDate = '' } = {}) {
  const params = new URLSearchParams({
    page,
    page_size: pageSize,
    ...(map && { map }),
    ...(startDate && { start_date: startDate }),
    ...(endDate && { end_date: endDate }),
  });
  return apiFetch(`/history?${params}`);
}
```

---

## agentImage.js

**위치:** `src/lib/agentImage.js`

### 역할

요원 이름을 valorant-api.com의 UUID로 변환 후 이미지 URL을 반환.

### 매핑 테이블

```js
const AGENT_UUIDS = {
  'Jett':     'add6443a-41bd-e414-f6ad-e58d267f4e95',
  'Phoenix':  'eb93336a-449b-9c1b-0a54-a891f7921d69',
  'Sage':     '569fdd95-4d10-43ab-ca70-79becc718b46',
  'Sova':     '320b2a48-4d9b-a075-30f1-1f93a9b638fa',
  'Viper':    '707eab51-4836-f488-046a-cda6bf494859',
  'Cypher':   '117ed9e3-49f3-6512-3ccf-0cada7e3823b',
  'Brimstone':'9f0d8ba9-4140-b941-57d3-a7ad57c6b417',
  'Omen':     '8e253930-4c05-31dd-1b6c-968525494517',
  'Breach':   '5f8d3a7f-467b-97f3-062c-13acf203c006',
  'Raze':     'f94c3b30-42be-e959-889c-5aa313dba261',
  'Killjoy':  '1dbf2edd-4729-0984-3115-daa5eed44993',
  'Skye':     '6f2a04ca-43e0-be17-7f36-b3908627744d',
  'Yoru':     '7f94d92c-4234-0a36-9646-3a87eb8b5c89',
  'Astra':    '41fb69c1-4189-7b37-f117-bcaf1e96f1bf',
  'KAY/O':    '601ddf7d-4b6f-7b61-0000-4e67a23f0000',
  'Chamber':  '22697054-9ac4-4581-7822-2a14d1f21e2f',
  'Neon':     'bb2a4828-46eb-8cd1-e765-15848195d751',
  'Fade':     'dade69b4-4f5a-8528-247b-219e5a1facd6',
  'Harbor':   '95b78ed7-4637-86d9-7e41-71ba8c293152', // ⚠️ 미검증
  'Gekko':    'e370fa57-4757-3604-3648-499e1f642d3f', // ⚠️ 미검증
  'Deadlock': 'cc8b64c8-4b25-4ff9-6e7f-37b4da43d235',
  'Iso':      '0e38b510-41a8-5780-7db2-6c7b66d56b88',
  'Clove':    '1dbf2edd-4729-1000-3115-daa5eed44993', // ⚠️ 미검증
  'Vyse':     'efba5359-4016-a1e5-7626-b1ae7aa000d5',
  'Tejo':     'c21ab44a-4aa4-5a60-4a47-7b548b78caab', // ⚠️ 미검증
  'Waylay':   'ebc736cd-9f1c-4ad7-a928-d42cc9bc77b0', // ⚠️ 미검증
};
```

> ⚠️ `Harbor`, `Gekko`, `Clove`, `Tejo`, `Waylay`는 UUID가 플레이스홀더이거나 미검증.
> 실제 UUID는 [valorant-api.com/v1/agents](https://valorant-api.com/v1/agents) API에서 확인.

### 내보내는 함수

```js
export function getAgentIconUrl(agentName) {
  const uuid = AGENT_UUIDS[agentName];
  if (!uuid) {
    console.warn(`[agentImage] Unknown agent: ${agentName}`);
    return '/images/unknown-agent.png'; // fallback
  }
  return `https://media.valorant-api.com/agents/${uuid}/displayicon.png`;
}

export function getAgentBustUrl(agentName) {
  const uuid = AGENT_UUIDS[agentName];
  if (!uuid) return '/images/unknown-agent.png';
  return `https://media.valorant-api.com/agents/${uuid}/bustportrait.png`;
}
```

### 이미지 도메인 등록 (next.config.mjs)

```js
images: {
  remotePatterns: [
    {
      protocol: 'https',
      hostname: 'media.valorant-api.com',
    },
  ],
}
```

이 설정 없으면 Next.js `<Image />` 컴포넌트가 외부 이미지 차단.
