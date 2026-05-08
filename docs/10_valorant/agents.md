# agents.md — 발로란트 27개 요원 도메인 카드

작성: 2026-05-09
출처 정책: 모든 메타 수치는 `sources.md`에 등록된 Riot 공식 / Liquipedia / VLR.gg 링크에 근거.
픽률은 **2024-2025 VCT 프로 매치 추정 범위**이며, US-002/US-004 데이터 통계로 cross-validation 예정.

요원 분류는 `ml/agent_roles.py`의 `AGENT_ROLE_MAP` 기준 (코드 기준 27개) + **2026-05-09 웹 검증으로 확인된 신규 2명** (Liquipedia/Riot 공식 검증) = 총 **29개**:

- **Duelist (타격대) 8종** — Jett, Phoenix, Raze, Reyna, Yoru, Neon, ISO, Waylay
- **Initiator (척후대) 7종** — Sova, Skye, Breach, KAY/O, Fade, Gekko, Tejo
- **Controller (전략가) 7종** — Brimstone, Viper, Omen, Astra, Harbor, Clove, **Miks** (2026-03 출시, 신규)
- **Sentinel (감시자) 7종** — Cypher, Killjoy, Sage, Chamber, Deadlock, Vyse, **Veto** (2025-10 출시, 신규)

⚠️ **코드 동기화 필요**: `ml/agent_roles.py`의 `AGENT_ROLE_MAP`에 Miks/Veto 미등록 상태. `normalize_agent("Miks")` / `normalize_agent("Veto")` 호출 시 None 반환. US-002에서 코드 동기화 + 데이터셋(visualize25 SQLite, vct_2025) 신규 요원 row 처리 필요.

각 요원 카드 형식:
```
### 요원명 (역할군)
- 능력 (Q/E/C/X): ...
- 강한 맵 (도메인): ...
- 시너지: ...
- 카운터 받음: ...
- 메타 위상 (픽률 추정): ...
- 도메인 가설 (cross-validation 후보): ...
- 출처: ...
```

도메인 가설은 **데이터 통계로 검증 가능한 형태**로 작성. US-005 cross-validation에서 CONFIRMED / CONTRADICTED / REFINED 분류.

---

## 출처 라벨 → sources.md anchor 매핑

본 문서에서 사용되는 모든 출처 라벨은 `sources.md`의 번호 항목으로 추적된다.

| 인라인 라벨 (이 문서) | sources.md anchor | URL |
|---------------------|-------------------|-----|
| `[Riot {요원명} 페이지]`, `[Riot Agents Page]` | [S-2] | https://playvalorant.com/en-us/agents/ |
| `[Liquipedia {요원명}]`, `[Liquipedia main]` | [S-15] | https://liquipedia.net/valorant/Main_Page |
| `[VLR.gg {요원명} stats]`, `[VLR.gg agent stats]` | [S-26] | https://www.vlr.gg/stats |
| `[VLR.gg pro match]`, `[VLR.gg main]` | [S-25] | https://www.vlr.gg/ |
| `[Riot 7.04 patch notes]`, `[Riot 7.04 패치]` | [S-1] (인덱스 통해 7.04) | https://playvalorant.com/en-us/news/game-updates/ |
| `[Riot 7.12 출시]` (ISO) | [S-5] | https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-7-12/ |
| `[Riot 8.0 패치]`, `[Riot 8.0 patch notes]` | [S-6] | https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-8-0/ |
| `[Riot 8.05 출시]` (Clove), `[Riot 8.05 patch notes]` | [S-7] | https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-8-05/ |
| `[Riot 8.08 patch notes]` (Cypher 너프) | [S-8] | https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-8-08/ |
| `[Riot 8.11 너프]`, `[Riot 8.11 patch notes]` (Abyss) | [S-9] | https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-8-11/ |
| `[Riot 9.0 출시]` (Vyse) | [S-10] | https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-9-00/ |
| `[Riot 9.05 너프]` (ISO/Sage) | [S-11] | https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-9-05/ |
| `[Riot 10.0 출시]` (Tejo) | [S-12] | https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-10-00/ |
| `[Riot 10.06 출시 발표]` (Waylay) | [S-13] | https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-10-06/ |
| `[VCT 2024 Champions Tokyo]` | [S-18] | https://liquipedia.net/valorant/Valorant_Champions/2024 |
| `[VCT 2024 Champions Tokyo 통계]` | [S-18]+[S-26] | Liquipedia + VLR.gg 결합 |
| `[VCT pro 매치]` | [S-16] (VCT 2024) | https://liquipedia.net/valorant/Valorant_Champions_Tour/2024 |

추가 라벨이 발견되면 본 표를 갱신하고 `sources.md`에 신규 항목 추가.

---

## Duelist (타격대) 8종

### Jett
- 능력: Q=Updraft(상승 점프), E=Tailwind(차징 대시, 시그니처), C=Cloudburst(소형 스모크), X=Blade Storm(수리검 — kill 시 recharge ult, **8 orb**) — Liquipedia 검증 (2026-05-09)
- 강한 맵: Haven, Split, Ascent, Fracture (수직 이동·복합 통로)
- 시너지: Sova (정보 후 dash entry), Killjoy (사이트 락다운 후 회전), Omen (smoke entry 보강)
- 카운터 받음: Cypher trip(대시 도착 지점 반응), Killjoy turret+ult, KAY/O ZERO/point(대시 봉쇄)
- 메타 위상: 2024-2025 VCT 픽률 추정 25-40%, 전형적 entry duelist
- 도메인 가설: **"Jett 보유 팀은 first-blood 획득률 +5%p"** (출처: VCT 2024 Champions Tokyo 통계)
- 출처: [Riot Jett 페이지], [Liquipedia Jett], [VLR.gg agent stats]

### Phoenix
- 능력: Q=Hot Hands(자가 회복 화염병), E=Curveball(커브 플래시, 시그니처), C=Blaze(화염 벽), X=Run It Back(자가 부활 ult, **6 orb**) — Liquipedia 검증 (2026-05-09)
- 강한 맵: Bind, Haven (좁은 통로 self-flash 효율)
- 시너지: Viper (벽 + 화염 진영 압박), Skye (플래시 중첩)
- 카운터 받음: KAY/O ult(자가 부활 봉쇄), Cypher cam, Omen TP(회전 압박)
- 메타 위상: 2024 7.04 패치 버프 후 픽률 5-10%, 솔로 캐리형
- 도메인 가설: **"Phoenix는 Skye/Sova 시너지 시 entry 라운드 승률 +5%p"**
- 출처: [Riot 7.04 패치], [VLR.gg Phoenix stats]

### Raze
- 능력: Q=Blast Pack(자폭 점프), E=Paint Shells(분열 수류탄, 시그니처), C=Boom Bot(탐색 봇), X=Showstopper(로켓 발사기 ult, **8 orb**) — Liquipedia 검증 (2026-05-09)
- 강한 맵: Bind, Split, Pearl, Fracture (좁은 통로 폭발 효율)
- 시너지: Brimstone (smoke + nade combo), KAY/O (suppress + ult 콤보), Skye (플래시 entry)
- 카운터 받음: Killjoy ult Lockdown(Showstopper 봉쇄 가능), Sova drone, Cypher trip
- 메타 위상: 2024-2025 픽률 15-25%, Bind/Split 메타 의존
- 도메인 가설: **"Bind에서 Raze는 Jett 대비 박빙 매치 승률 +3%p"**
- 출처: [Riot Raze 페이지], [VLR.gg Bind stats]

### Reyna
- 능력: Q=Devour(soul orb 흡수 회복), E=Dismiss(soul orb 흡수 무적 회피), C=Leer(플래시 안구, 시그니처), X=Empress(연사·재장전 가속 + 무한 charges ult, **6 orb**) — Liquipedia 검증 (2026-05-09)
- 강한 맵: 솔로 캐리형이라 맵 의존 약함 (Fracture, Sunset에서 픽률 약간 ↑)
- 시너지: Sova (정보), Skye (플래시 보강)
- 카운터 받음: 팀게임 강한 조합 (KAY/O + Fade), Cypher (정보), Killjoy
- 메타 위상: 프로 매치 픽률 <2% (2024 8.05 너프 후), 랭크전 하이 픽
- 도메인 가설: **"Reyna 보유 팀은 프로 매치에서 라운드 승률 -2%p"** (CONTRADICTED 후보 — 데이터로 검증 필요)
- 출처: [Riot 8.05 패치 노트], [Liquipedia Reyna]

### Yoru
- 능력: Q=Blindside(반사 플래시), E=Gatecrash(rift tether TP, 시그니처), C=Fakeout(클론 데코이), X=Dimensional Drift(투명·무적 ult, **8 orb**) — Liquipedia 검증 (2026-05-09)
- 강한 맵: Bind, Breeze (TP 활용 회전 압박)
- 시너지: Sova (정보 후 lurk), Cypher (락다운 동안 lurk)
- 카운터 받음: Fade Haunt(클론·TP 위치 노출), Sova drone, Cypher cam
- 메타 위상: 2024 8.0 버프 후 픽률 3-8%, 프로 게임 일부 활용
- 도메인 가설: **"Yoru는 lurker 역할 한정 효율 — 솔로 entry 시 Jett/Raze 대비 승률 -3%p"**
- 출처: [Riot 8.0 패치], [VLR.gg Yoru]

### Neon
- 능력: Q=Relay Bolt(반사 스턴), E=High Gear(전기 슬라이드, 시그니처), C=Fast Lane(2겹 전기 벽), X=Overdrive(전기 빔 ult, **7 orb**) — Liquipedia 검증 (2026-05-09)
- 강한 맵: Breeze, Icebox, Sunset (긴 거리 빠른 회전)
- 시너지: KAY/O (suppress + 빠른 entry), Sova (정보)
- 카운터 받음: Cypher trip(슬라이드 봉쇄), Killjoy turret, Deadlock GravNet
- 메타 위상: 2024 8.11/9.x 너프 → 2025 부분 회복, 픽률 8-15%
- 도메인 가설: **"Neon은 long-distance map(Breeze/Icebox)에서 Jett 대비 entry 효율 +5%p"**
- 출처: [Riot 8.11 패치], [VLR.gg Breeze stats]

### ISO
- 능력: Q=Undercut(취약성 + suppress 디버프), E=Double Tap(flow state — 데미지 시 orb 생성, 시그니처), C=Contingency(파괴 불가 에너지 벽), X=Kill Contract(1v1 결투장 ult, **7 orb**) — Liquipedia 검증 (2026-05-09)
- 출시: 2023년 10월 31일 (패치 7.09)
- 강한 맵: Pearl, Lotus, Sunset (1v1 favorable 통로)
- 시너지: Cypher (정보 → 1v1 강제), Killjoy (락다운 + ult 결투)
- 카운터 받음: 다중 압박 조합 (Skye + Sova + Raze), Breach
- 메타 위상: 2024 H2 챔피언스 픽률 급등(40%+) → 2024 9.05 너프 후 10-20%
- 도메인 가설: **"ISO는 박빙 매치에서 1v1 ult 라운드 승률 +3%p"**
- 출처: [Riot 7.12 출시], [Riot 9.05 너프], [VCT 2024 Champions]

### Waylay
- 능력: Q=Light Speed(이중 대시), E=Refract(floor beacon 후 invulnerable light mote 귀환, 시그니처 — 2 kill 시 회복), C=Saturate(빛 cluster — 이동·무기 slow), X=Convergent Paths(afterimage beam — speed boost + hinder ult, **8 orb**) — Liquipedia 검증 (2026-05-09)
- 출시: 2025년 3월 5일 (패치 10.04)
- 강한 맵: Lotus, Fracture (3단 대시 + 다층 구조)
- 시너지: Killjoy (락다운 + 광속 entry), Sova
- 카운터 받음: KAY/O suppress(대시 봉쇄), Cypher trip
- 메타 위상: 2025 H1 출시 → 픽률 5-12% (학습 곡선)
- 도메인 가설: **"Waylay는 출시 직후 픽률 ↑이지만 박빙 승률은 데이터 부족 — REFINED 후보"**
- 출처: [Riot 10.06 출시 발표], [VLR.gg Waylay early stats]

---

## Initiator (척후대) 7종

### Sova
- 능력: Q=Shock Bolt(피해 화살, 1-75 damage), E=Recon Bolt(정찰 화살 — 2 scans, 시그니처, 40s cooldown), C=Owl Drone(7s fuel 원격 드론), X=Hunter's Fury(3발 관통 화살 ult, **8 orb**) — Liquipedia 검증 (2026-05-09)
- 강한 맵: Ascent, Icebox, Breeze, Haven (오픈 사이트 라인)
- 시너지: Jett (정보 → entry), Killjoy (정보 + 락), Brimstone (smoke + 정보)
- 카운터 받음: Viper Toxic Screen(화살 차단), Harbor 벽, Cypher cam vs drone
- 메타 위상: 픽률 30-50% (전 메타 stable initiator)
- 도메인 가설: **"Sova는 어느 맵에서도 stable — 보유 팀 정보 차이로 라운드 승률 +2-4%p"**
- 출처: [Riot Sova], [VLR.gg agent stats]

### Skye
- 능력: Q=Trailblazer(원격 호랑이 정찰), E=Guiding Light(플래시 새, 시그니처), C=Regrowth(팀·자가 힐), X=Seekers(3타깃 추적 ult, **7 orb**) — Liquipedia 공식 검증 (2026-05-09)
- 강한 맵: Haven, Lotus, Bind (다중 사이트 정보)
- 시너지: Reyna/Jett (entry flash), Sage (heal stack)
- 카운터 받음: KAY/O suppress(플래시·힐 무력화), Sova drone
- 메타 위상: 픽률 25-40% (안정적)
- 도메인 가설: **"Skye는 플래시·힐 hybrid — 다이브 조합 라운드 승률 +3%p"**
- 출처: [Riot Skye], [VLR.gg Skye]

### Breach
- 능력: Q=Flashpoint(벽 관통 플래시, 2 charges), E=Fault Line(seismic concuss, 시그니처, 35s cooldown), C=Aftershock(그라운드 폭발 60 dmg), X=Rolling Thunder(광역 연쇄 스턴 ult, **9 orb**) — Liquipedia 검증 (2026-05-09)
- 강한 맵: Pearl, Bind, Lotus (좁은 통로)
- 시너지: Raze, Phoenix, Jett (entry flash + stun)
- 카운터 받음: KAY/O suppress, 오픈 맵(Ascent — 벽 활용 부족), Sage barrier
- 메타 위상: 픽률 10-20% (특정 맵 한정)
- 도메인 가설: **"Breach는 Pearl/Bind에서 entry first-blood 획득률 +6%p"**
- 출처: [Riot Breach], [VLR.gg Pearl stats]

### KAY/O
- 능력: Q=FLASH/drive(플래시), E=ZERO/point(투척 서프레스 칼, 시그니처), C=FRAG/ment(분열 수류탄), X=NULL/cmd(광역 12초 서프레스 ult, **7 orb**) — Liquipedia 검증 (2026-05-09)
- 강한 맵: 모든 맵 (메타 의존)
- 시너지: Raze (suppress + ult), Jett (suppress + entry), Killjoy
- 카운터 받음: 카운터 적음 — 일반적으로 stable, Cypher cam
- 메타 위상: 픽률 20-35% (anti-utility 메타)
- 도메인 가설: **"KAY/O 보유 팀은 ult 메타에서 적팀 ult 효율 -8%p (suppress로 ult 봉쇄)"**
- 출처: [Riot KAY/O], [VLR.gg KAY/O]

### Fade
- 능력: Q=Seize(그래스 결박), E=Haunt(위치 표시 안구, 시그니처), C=Prowler(공포 짐승), X=Nightfall(공포·위치 ult, **8 orb**) — Liquipedia 검증 (2026-05-09)
- 강한 맵: Lotus, Haven, Pearl (다중 사이트 정보)
- 시너지: Jett (정보 → entry), Killjoy
- 카운터 받음: KAY/O suppress, Cypher cam, Yoru clone(데코이로 Haunt 낭비 유도)
- 메타 위상: 픽률 15-25% (Sova 대체)
- 도메인 가설: **"Fade는 Lotus에서 Sova 대비 entry 정보 우위 +3%p (3 사이트 동시 정보)"**
- 출처: [Riot Fade], [VLR.gg Lotus stats]

### Gekko
- 능력: Q=Wingman(소환수 — 플래시/스파이크 운반), E=Dizzy(plasma blast 플래시 페트, 시그니처), C=Mosh Pit(그라운드 폭발), X=Thrash(사이트 폭파 + detain ult, **7 orb**) — Liquipedia 검증 (2026-05-09)
- 출시: 2023년 3월 7일 (패치 6.04)
- 강한 맵: Sunset, Pearl, Lotus
- 시너지: Brimstone (smoke + nade combo), Cypher
- 카운터 받음: Sova drone(소환수 노출 후 파괴), Cypher trip
- 메타 위상: 2024-2025 안정 픽률 15-25%
- 도메인 가설: **"Gekko는 7 orb ult로 다른 initiator(Breach/Tejo 9-orb) 대비 ult 사이클 +1회/맵"** (실측 ult cost 7 orb — Liquipedia 검증)
- 출처: [Riot 6.04 출시], [VLR.gg Gekko]

### Tejo
- 능력: Q=Special Delivery(스턴 sticky grenade), E=Guided Salvo(가이드 미사일 2발 — 자율 navigate, 시그니처), C=Stealth Drone(드론 — pulse로 suppress + reveal), X=Armageddon(광역 폭격 ult — 30m 경로, **9 orb**) — Liquipedia 검증 (2026-05-09)
- 출시: 2025년 1월 (패치 10.0)
- 강한 맵: Ascent, Sunset (오픈 사이트)
- 시너지: Jett (정보 + entry), Killjoy (락 + 폭격)
- 카운터 받음: Viper Toxic Screen(미사일 차단), KAY/O(드론 suppress)
- 메타 위상: 2025 H1 출시 직후 픽률 30-50% (over-tuned 가능성)
- 도메인 가설: **"Tejo는 출시 직후 over-tuned — 픽률 vs 승률 차이 추적, REFINED 후보"**
- 출처: [Riot 10.0 출시], [VLR.gg Tejo early stats]

---

## Controller (전략가) 6종

### Brimstone
- 능력: Q=Incendiary(화염 그레네이드), E=Sky Smoke(3개 즉발 스모크, 시그니처), C=Stim Beacon(공격 속도·연사 부스트), X=Orbital Strike(광역 폭격 ult, **8 orb**) — Liquipedia 검증 (2026-05-09)
- 강한 맵: Bind, Breeze, Split (즉시 스모크 활용)
- 시너지: Raze (smoke + nade), Phoenix (closed-comp), KAY/O
- 카운터 받음: Astra (글로벌 스모크 우위), 오픈 맵(Ascent — 스모크 거리 부족)
- 메타 위상: 픽률 15-25% (특정 맵 한정)
- 도메인 가설: **"Brimstone은 Breeze에서 즉발 스모크로 어택 라운드 승률 +4%p"**
- 출처: [Riot Brimstone], [VLR.gg Breeze stats]

### Viper
- 능력: Q=Poison Cloud(재사용 스모크 구체), E=Toxic Screen(긴 가스 벽, 시그니처), C=Snake Bite(가스 화염), X=Viper's Pit(광역 가스 ult, **9 orb**) — Liquipedia 검증 (2026-05-09)
- 강한 맵: Icebox, Breeze, Pearl, Fracture, Bind (긴 사이트 라인)
- 시너지: Killjoy (락 + 가스), Sova (정보 + 차단)
- 카운터 받음: KAY/O ult(가스 효과 일부 무력화), Skye (플래시), Sage
- 메타 위상: 픽률 30-50% (Icebox/Breeze 사실상 100%)
- 도메인 가설: **"Viper는 Icebox/Breeze에서 부재 시 어택 라운드 승률 -8%p"**
- 출처: [Riot Viper], [VCT 2024 Icebox 통계]

### Omen
- 능력: Q=Paranoia(눈 가림 투사체), E=Dark Cover(장거리 스모크, 시그니처), C=Shrouded Step(단거리 TP), X=From the Shadows(글로벌 TP ult, **7 orb**) — Liquipedia 검증 (2026-05-09)
- 강한 맵: Haven, Sunset, Lotus, Ascent (TP 활용)
- 시너지: Jett (smoke entry), Sova (정보), Cypher
- 카운터 받음: Cypher cam(TP 위치 노출), Killjoy turret, Sova
- 메타 위상: 픽률 30-45% (most stable controller)
- 도메인 가설: **"Omen은 universal pick — 어느 맵에서도 라운드 승률 영향 ±2%p 이내"**
- 출처: [Riot Omen], [VLR.gg Omen]

### Astra
- 능력: Astral Form(시그니처, 별 배치 모드 전환) + 별 활성화 3종 — Q=Nova Pulse(스턴), E=Nebula(원격 스모크, F로 Dissipate 회수), C=Gravity Well(중력 결박), X=Cosmic Divide(글로벌 음향·시야 차단 벽 ult, **7 orb**). 별은 매 라운드 150 credits, 4개 max, 25초 cooldown — Liquipedia 공식 검증 (2026-05-09)
- 강한 맵: Haven, Lotus, Bind (다중 사이트)
- 시너지: Cypher (정보 + 별 컨트롤), Sage
- 카운터 받음: 빠른 entry (Raze, Jett — 별 셋업 전 압박), KAY/O suppress
- 메타 위상: 픽률 5-15% (skill ceiling 높음)
- 도메인 가설: **"Astra는 high-skill 팀에서만 효율 — Tier 1 매치에서 라운드 승률 +3%p, Tier 2에서 -2%p"**
- 출처: [Riot Astra], [VCT 2024 vs Challengers 비교]

### Harbor
- 능력: Q=Cove(원형 물 방어 돔, 시그니처), E=High Tide(긴 가이드 물 벽), C=Storm Surge(원격 whirlpool — nearsight + slow), X=Reckoning(광역 물 폭격 ult, **7 orb**) — Liquipedia 검증 (2026-05-09). ⚠️ "Cascade"는 미존재, 실제 C 슬롯은 "Storm Surge"
- 출시: 2022년 10월 18일 (패치 5.08)
- 강한 맵: Sunset, Bind, Pearl, Lotus
- 시너지: Viper (double controller), Brimstone
- 카운터 받음: Astra (글로벌 우위), Omen (smoke + TP)
- 메타 위상: 픽률 5-15% (2nd controller로 활용)
- 도메인 가설: **"Harbor는 double-controller 조합에서만 효율 — sole controller 시 라운드 승률 -4%p"**
- 출처: [Riot 5.08 출시], [VLR.gg Harbor]

### Clove
- 능력: Q=Meddle(취약성 grenade), E=Ruse(post-mortem 원격 스모크, 시그니처), C=Pick-me-up(킬 후 자가 부활·부스트), X=Not Dead Yet(자가 부활 ult, **7 orb**) — Liquipedia 공식 검증 (2026-05-09)
- 출시: 2024년 3월 26일 (패치 8.05) — Riot 공식 검증
- 강한 맵: 모든 맵 (universal duelist-controller hybrid)
- 시너지: Jett (entry + smoke), Killjoy (락 + ult 부활)
- 카운터 받음: KAY/O ult(suppress로 부활 봉쇄), Cypher
- 메타 위상: 출시 직후 픽률 60%+ → 2024 8.11 너프 후 30-40%
- 도메인 가설: **"Clove는 controller 역할의 'duelist' 변종 — entry + smoke hybrid로 박빙 라운드 승률 +5%p"**
- 출처: [Riot 8.05 출시], [Riot 8.11 너프], [VLR.gg Clove]

### Miks (신규 — 2026-05-09 웹 검증으로 확인)
- 능력: Q=Harmonize(아군·자가 Combat Stim), E=Waveform(원격 스모크 2회 충전, 시그니처), C=M-Pulse(Concuss/Healing 토글 음파, 250c, 2회 충전), X=Bassquake(전방 음파 펄스 — knockback + Deafen + Slow ult, **8 orb**)
- 출시: 2026년 3월 17일 (패치 12.05) — Liquipedia 검증
- 출신: 크로아티아
- 강한 맵: 데이터 부족 (출시 직후) — 추정: Multi-site 맵에서 Waveform 2회 활용
- 시너지: 데이터 부족
- 카운터 받음: 데이터 부족
- 메타 위상: 2026 출시 직후 — VCT 정착 데이터 미수집
- 도메인 가설: **"Miks는 출시 직후 over-tuned 가능성 — 8-orb ult로 사이클이 느리지만 광역 디버프 효율 ↑, REFINED 후보"**
- 출처: [Liquipedia Miks], [Riot 12.05 패치 노트]

---

## Sentinel (감시자) 7종

### Cypher
- 능력: Q=Cyber Cage(시야 차단 cage), E=Spycam(원격 CCTV·다트, 시그니처), C=Trapwire(트립와이어), X=Neural Theft(시체 정보 ult, **6 orb**) — Liquipedia 검증 (2026-05-09)
- 강한 맵: Pearl, Sunset, Bind, Ascent (좁은 회전 통로)
- 시너지: Sova, Brimstone, Viper
- 카운터 받음: Raze ult(Showstopper로 utility 파괴), Skye Trailblazer(cam 파괴), 빠른 entry
- 메타 위상: 픽률 30-50% (most stable sentinel, 6 orb로 ult 사이클 빠름)
- 도메인 가설: **"Cypher는 Pearl/Sunset에서 부재 시 수비 라운드 승률 -6%p"**
- 출처: [Riot Cypher], [VCT 2024 Pearl 통계]

### Killjoy
- 능력: Q=Alarmbot(자살 디버프 봇, vulnerable 적용), E=Turret(자동 사격 터렛, 시그니처), C=Nanoswarm(원격 그라운드 폭발 — 45 DPS), X=Lockdown(광역 13초 detain ult, **9 orb**) — Liquipedia 검증 (2026-05-09)
- 강한 맵: Ascent, Icebox, Sunset (사이트 락)
- 시너지: Viper (락 + 가스), Sova (정보 + 락), Raze
- 카운터 받음: Raze ult(utility 파괴), Sova drone, Breach 스턴
- 메타 위상: 픽률 30-45% (Cypher와 양분)
- 도메인 가설: **"Killjoy는 Ascent에서 ult 사이클로 라운드 승률 +5%p"**
- 출처: [Riot Killjoy], [VCT 2024 Ascent 통계]

### Sage
- 능력: Q=Slow Orb(감속 grenade, 7s), E=Healing Orb(아군 60HP/5s 또는 자가 60HP/10s, 시그니처, 45s cooldown), C=Barrier Orb(**11.08 이후 600 HP** 벽, 비용 300c, fortification 2s — Liquipedia 검증), X=Resurrection(부활 ult, **7 orb**) — Liquipedia 검증 (2026-05-09)
- 강한 맵: Bind, Split, Icebox (좁은 통로 + 벽 활용)
- 시너지: Killjoy (이중 sentinel), Skye (heal stack)
- 카운터 받음: KAY/O suppress(벽 효과 일부 무력화), Breach(벽 관통 플래시)
- 메타 위상: 픽률 5-15% (특정 맵 한정)
- 도메인 가설: **"Sage는 Bind에서 wall로 회전 차단 시 수비 라운드 승률 +3%p"**
- 출처: [Riot Sage], [VLR.gg Bind stats]

### Chamber
- 능력: Q=Headhunter(헤드헌터 헤비 권총 — 100c/탄, 8발), E=Rendezvous(2-앵커 TP, 시그니처, 30s cooldown / 45s 파괴 시), C=Trademark(원격 스캔 트랩 + slow), X=Tour de Force(저격총 ult — 5발, **8 orb**) — Liquipedia 검증 (2026-05-09)
- 강한 맵: Breeze, Icebox, Pearl (long-range)
- 시너지: Viper (가스 + 저격), Sova
- 카운터 받음: 2024-2025 너프 후 활용도 ↓, Fade Haunt(앵커 위치 노출), Breach 스턴
- 메타 위상: 2022 메타 → 2023 4.08 + 5.08 너프 → 2024 픽률 5-10%, 2025 부분 회복
- 도메인 가설: **"Chamber는 long-range map 한정 활용 — Breeze에서만 픽률 ≥15%"**
- 출처: [Riot 4.08 너프], [Riot 5.08 너프], [VLR.gg Chamber timeline]

### Deadlock
- 능력: Q=Sonic Sensor(움직임 감지 + 광역 concuss), E=GravNet(crouch + slow grenade, 시그니처, 40s cooldown), C=Barrier Mesh(차단 벽 disc), X=Annihilation(nanowire pulse — 첫 적 capture & pull ult, **7 orb**) — Liquipedia 검증 (2026-05-09)
- 출시: 2023년 6월 (패치 7.0)
- 강한 맵: Icebox, Bind, Lotus
- 시너지: Viper (가스 + 차단), Sova (정보 + 락)
- 카운터 받음: 빠른 entry (Raze ult로 mesh 파괴), KAY/O suppress
- 메타 위상: 출시 후 → 2024 7.04 + 8.x 버프 → 픽률 10-25% (Cypher/Killjoy 대안)
- 도메인 가설: **"Deadlock은 Icebox에서 ult로 박빙 라운드 결정력 +4%p"**
- 출처: [Riot 7.0 출시], [Riot 7.04 버프], [VLR.gg Deadlock]

### Vyse
- 능력: Q=Shear(원격 돌출 벽 트랩), E=Arc Rose(원격 플래시 꽃, 시그니처), C=Razorvine(원격 razorvine 둥지), X=Steel Garden(광역 무기 잠금 ult, **8 orb**) — Liquipedia 검증 (2026-05-09)
- 출시: 2024년 8월 28일 (패치 9.04)
- 강한 맵: Bind, Sunset, Pearl
- 시너지: Cypher (이중 sentinel), Sova, Viper
- 카운터 받음: Raze ult(utility 파괴), KAY/O suppress, Breach
- 메타 위상: 출시 후 2024 H2 픽률 15-25%
- 도메인 가설: **"Vyse는 ult로 적팀 무기 봉쇄 — 박빙 매치에서 ult 라운드 승률 +6%p"**
- 출처: [Riot 9.0 출시], [VLR.gg Vyse]

### Veto (신규 — 2026-05-09 웹 검증으로 확인)
- 능력: Q=Chokehold(원격 hold trap — Deafen + Decay), E=Crosscut(2-앵커 TP, 시그니처 — buy phase 회수 가능), C=Interceptor(utility destroyer — 적 utility 자동 파괴, 무료 사용), X=Evolution(mutation 강화 ult, debuff 면역 + 전투 보너스, **7 orb** Liquipedia 검증 2026-05-09)
- 출시: 2025년 10월 7일 (패치 11.07b) — Riot 공식 검증
- 출신: 세네갈 (Senegal)
- 강한 맵: 데이터 부족 (TP signature로 회전 압박 활용 — Pearl/Sunset 추정)
- 시너지: Sova (정보 + Interceptor utility 보강), Viper
- 카운터 받음: KAY/O ult(mutation 효과 일부 봉쇄), Raze ult
- 메타 위상: 2025 H2 출시 → 픽률 데이터 수집 중
- 도메인 가설: **"Veto는 Interceptor로 적팀 utility 효율 -10%p (특히 Killjoy/Cypher 셋업 매치)"**
- 출처: [Liquipedia Veto], [Riot 11.07b 패치 노트]

---

## 도메인 가설 요약 (cross-validation 후보, 총 29개)

US-005 cross-validation에서 검증할 가설들. **CONFIRMED / CONTRADICTED / REFINED 분류 예정.**

| ID | 요원 | 가설 | 검증 데이터 |
|----|------|------|------------|
| H-JETT-FIRSTBLOOD | Jett | 보유 팀 first-blood +5%p | VCT 2024 first-blood log |
| H-PHOENIX-SYNERGY | Phoenix | Skye/Sova 시너지 시 entry +5%p | VCT 2024-2025 |
| H-RAZE-BIND | Raze | Bind에서 Jett 대비 박빙 +3%p | Bind 매치 박빙 표본 |
| H-REYNA-PRO | Reyna | 프로 매치 라운드 승률 -2%p | VCT pro 매치 |
| H-YORU-LURKER | Yoru | solo entry 시 -3%p | VCT 2024-2025 entry log |
| H-NEON-LONGMAP | Neon | Breeze/Icebox entry +5%p | Breeze/Icebox stats |
| H-ISO-CLOSE | ISO | 박빙 ult 라운드 +3%p | margin=2 매치 |
| H-WAYLAY-EARLY | Waylay | 출시 직후 픽률 vs 승률 괴리 | 2025 H1 |
| H-SOVA-STABLE | Sova | 모든 맵 +2-4%p | 전체 데이터 |
| H-SKYE-DIVE | Skye | 다이브 조합 +3%p | Skye+duelist combo |
| H-BREACH-PEARLBIND | Breach | Pearl/Bind first-blood +6%p | Pearl/Bind 매치 |
| H-KAYO-ULTMETA | KAY/O | 적팀 ult 효율 -8%p | ult 라운드 표본 |
| H-FADE-LOTUS | Fade | Lotus entry +3%p | Lotus 매치 |
| H-GEKKO-ORBCYCLE | Gekko | Gekko 7-orb는 다른 9-orb initiator(Breach/Tejo) 대비 맵당 ult +1회 | ult 사이클 카운트 |
| H-TEJO-OVERTUNED | Tejo | 출시 직후 over-tuned | 2025 H1 픽 vs 승률 |
| H-BRIM-BREEZE | Brimstone | Breeze 어택 +4%p | Breeze 어택 라운드 |
| H-VIPER-ICEBOX | Viper | Icebox/Breeze 부재 시 -8%p | Viper 부재 매치 |
| H-OMEN-UNIVERSAL | Omen | 맵 영향 ±2%p | 전체 |
| H-ASTRA-TIER | Astra | Tier 1 +3%p, Tier 2 -2%p | tier별 분리 |
| H-HARBOR-DOUBLE | Harbor | sole controller 시 -4%p | Harbor 단독 매치 |
| H-CLOVE-CLOSE | Clove | 박빙 라운드 +5%p | margin=2 매치 |
| H-CYPHER-PEARLSUNSET | Cypher | Pearl/Sunset 부재 시 -6%p | Cypher 부재 매치 |
| H-KJ-ASCENT | Killjoy | Ascent +5%p | Ascent 매치 |
| H-SAGE-BIND | Sage | Bind 수비 +3%p | Bind 수비 라운드 |
| H-CHAMBER-LONGRANGE | Chamber | Breeze 픽률 ≥15% | Breeze stats |
| H-DEADLOCK-ICEBOX | Deadlock | Icebox 박빙 +4%p | Icebox 박빙 |
| H-VYSE-CLOSE | Vyse | 박빙 ult 라운드 +6%p | Vyse ult 라운드 |
| H-MIKS-NEW | Miks | 출시 직후 over-tuned 가능성 — REFINED 후보 | 2026 H1 |
| H-VETO-INTERCEPTOR | Veto | Interceptor 보유 시 적팀 utility 효율 -10%p | Veto vs Killjoy/Cypher 매치 |

총 **29개 가설** (요원당 ≥1, 신규 2명 포함) — US-005 cross-validation에서 데이터로 양방향 검증.

---

## 메모

- 픽률 수치는 **추정 범위**. US-002에서 VLR.gg + Kaggle vct_2024/2025 데이터로 정확한 수치 산출 후 업데이트.
- 출처는 모두 `sources.md`에 등록된 Riot 공식 / Liquipedia / VLR.gg 만 사용 (커뮤니티 글 제외).
- 가설 ID 명명 규칙: `H-{AGENT}-{CONTEXT}` (예: `H-JETT-FIRSTBLOOD`).
- US-005에서 27개 가설을 모두 `validate_domain_hypothesis()` 입력으로 사용.
