// 발로란트 공개 에셋(valorant-api.com) 이미지 매핑.
// 요원 29 · 맵 13 모두 이름→UUID 로 해석해 media CDN URL 을 만든다.
// 사용자 선택(맵/요원)에 따라 실제 이미지가 동적으로 표시된다 (런타임 CDN 직접 링크).
// UUID 출처: https://valorant-api.com/v1/agents , /v1/maps (2026-06 기준).

const CDN = "https://media.valorant-api.com";

// 정규화: 소문자 + 영숫자만 (예: "KAY/O"→"kayo", "ISO"→"iso")
const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, "");

const AGENT_UUID: Record<string, string> = {
  jett: "add6443a-41bd-e414-f6ad-e58d267f4e95",
  reyna: "a3bfb853-43b2-7238-a4f1-ad90e9e46bcc",
  phoenix: "eb93336a-449b-9c1b-0a54-a891f7921d69",
  raze: "f94c3b30-42be-e959-889c-5aa313dba261",
  yoru: "7f94d92c-4234-0a36-9646-3a87eb8b5c89",
  neon: "bb2a4828-46eb-8cd1-e765-15848195d751",
  iso: "0e38b510-41a8-5780-5e8f-568b2a4f2d6c",
  waylay: "df1cb487-4902-002e-5c17-d28e83e78588",
  sova: "320b2a48-4d9b-a075-30f1-1f93a9b638fa",
  breach: "5f8d3a7f-467b-97f3-062c-13acf203c006",
  skye: "6f2a04ca-43e0-be17-7f36-b3908627744d",
  kayo: "601dbbe7-43ce-be57-2a40-4abd24953621",
  fade: "dade69b4-4f5a-8528-247b-219e5a1facd6",
  gekko: "e370fa57-4757-3604-3648-499e1f642d3f",
  tejo: "b444168c-4e35-8076-db47-ef9bf368f384",
  viper: "707eab51-4836-f488-046a-cda6bf494859",
  omen: "8e253930-4c05-31dd-1b6c-968525494517",
  brimstone: "9f0d8ba9-4140-b941-57d3-a7ad57c6b417",
  astra: "41fb69c1-4189-7b37-f117-bcaf1e96f1bf",
  harbor: "95b78ed7-4637-86d9-7e41-71ba8c293152",
  clove: "1dbf2edd-4729-0984-3115-daa5eed44993",
  miks: "7c8a4701-4de6-9355-b254-e09bc2a34b72",
  killjoy: "1e58de9c-4950-5125-93e9-a0aee9f98746",
  cypher: "117ed9e3-49f3-6512-3ccf-0cada7e3823b",
  sage: "569fdd95-4d10-43ab-ca70-79becc718b46",
  chamber: "22697a3d-45bf-8dd7-4fec-84a9e28c69d7",
  deadlock: "cc8b64c8-4b25-4ff9-6e7f-37b4da43d235",
  vyse: "efba5359-4016-a1e5-7626-b1ae76895940",
  veto: "92eeef5d-43b5-1d4a-8d03-b3927a09034b",
};

const MAP_UUID: Record<string, string> = {
  ascent: "7eaecc1b-4337-bbf6-6ab9-04b8f06b3319",
  bind: "2c9d57ec-4431-9c5e-2939-8f9ef6dd5cba",
  haven: "2bee0dc9-4ffe-519b-1cbd-7fbe763a6047",
  split: "d960549e-485c-e861-8d71-aa9d1aed12a2",
  icebox: "e2ad5c54-4114-a870-9641-8ea21279579a",
  breeze: "2fb9a4fd-47b8-4e7d-a969-74b4046ebd53",
  fracture: "b529448b-4d60-346e-e89e-00a4c527a405",
  pearl: "fd267378-4d1d-484f-ff52-77821ed10dc2",
  lotus: "2fe4ed3a-450a-948b-6d6b-e89a78e680a9",
  sunset: "92584fbe-486a-b1b2-9faa-39b0f486b498",
  abyss: "224b0a95-48b9-f703-1bd8-67aca101a61f",
  drift: "2c09d728-42d5-30d8-43dc-96a05cc7ee9d",
  corrode: "1c18ab1f-420d-0d8b-71d0-77ad3c439115",
};

/** 요원 디스플레이 아이콘 (정사각 투명 흉상) — 아바타용 */
export function agentIcon(name?: string | null): string | null {
  if (!name) return null;
  const uuid = AGENT_UUID[norm(name)];
  return uuid ? `${CDN}/agents/${uuid}/displayicon.png` : null;
}

/** 요원 풀 포트레이트 (전신 스플래시) — 히어로 아트용 */
export function agentPortrait(name?: string | null): string | null {
  if (!name) return null;
  const uuid = AGENT_UUID[norm(name)];
  return uuid ? `${CDN}/agents/${uuid}/fullportrait.png` : null;
}

/** 맵 스플래시 (대형 배경 사진) — 배너/배경용 */
export function mapSplash(name?: string | null): string | null {
  if (!name) return null;
  const uuid = MAP_UUID[norm(name)];
  return uuid ? `${CDN}/maps/${uuid}/splash.png` : null;
}

/** 맵 리스트뷰 아이콘 (소형) */
export function mapListIcon(name?: string | null): string | null {
  if (!name) return null;
  const uuid = MAP_UUID[norm(name)];
  return uuid ? `${CDN}/maps/${uuid}/listviewicon.png` : null;
}
