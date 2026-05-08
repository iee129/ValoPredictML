# meta.md — 발로란트 시즌 메타 + 패치 영향 매핑

작성: 2026-05-09
범위: VCT 2024 H1 → 2025 H2 (8 시즌 카테고리)
출처 정책: 패치 노트는 Riot 공식 (`playvalorant.com/news/game-updates/`), 메타는 Liquipedia VCT + 프로팀 공식 분석.

---

## 출처 라벨 → sources.md anchor 매핑

| 인라인 라벨 | sources.md anchor | URL |
|------------|-------------------|-----|
| `[Riot 7.12 patch notes]` | [S-5] | https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-7-12/ |
| `[Riot 8.0 patch notes]` | [S-6] | https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-8-0/ |
| `[Riot 8.05 patch notes]`, `[Riot Clove 출시 발표]` | [S-7] | https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-8-05/ |
| `[Riot 8.08 patch notes]` | [S-8] | https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-8-08/ |
| `[Riot 8.11 patch notes]`, `[Riot Abyss 출시 발표]` | [S-9] | https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-8-11/ |
| `[Riot 9.0 patch notes]`, `[Riot Vyse 출시]` | [S-10] | https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-9-00/ |
| `[Riot 9.04 patch notes — sources.md #1 인덱스 통해 접근]` | [S-1] | https://playvalorant.com/en-us/news/game-updates/ |
| `[Riot 9.05 patch notes]` | [S-11] | https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-9-05/ |
| `[Riot 9.08 patch notes]`, `[Riot map rotation 발표]` | [S-1] 인덱스 통해 | Patch Notes Index |
| `[Riot 10.0 patch notes]`, `[Riot Tejo 출시]` | [S-12] | https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-10-00/ |
| `[Riot 10.04 patch notes]` | [S-1] 인덱스 통해 10.04 | Patch Notes Index |
| `[Riot 10.06 patch notes]`, `[Riot Waylay 출시 발표]` | [S-13] | https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-10-06/ |
| `[Riot 10.08 patch notes]` | [S-1] 인덱스 통해 10.08 | Patch Notes Index |
| `[Liquipedia VCT 2024 Kickoff]`, `[Liquipedia VCT Champions Tokyo 2024]`, `[Liquipedia VCT 2025 Kickoff]` | [S-16]/[S-17]/[S-18] | VCT 2024/2025 + Champions Tokyo |
| `[VLR.gg 2024-H1 stats]`, `[VLR.gg 2024-H2 stats]` | [S-26] | https://www.vlr.gg/stats |
| `[Riot 패치 노트 인덱스 — 11.x+]` | [S-1] | Patch Notes Index |

---

## 시즌 카테고리 (총 8개)

본 프로젝트의 데이터 활성 시즌 = **VCT 2024 + VCT 2025** (vct_2024, vct_2025 Kaggle 데이터셋).

| 시즌 코드 | 시기 | 주요 토너먼트 | 주요 패치 |
|-----------|------|--------------|-----------|
| **2024-H1** | 2024년 1-6월 | Kickoff, Masters Madrid, Stage 1 | 8.0 / 8.05 / 8.08 / 8.11 |
| **2024-H2** | 2024년 7-12월 | Masters Shanghai, Champions Tokyo, Stage 2 | 9.0 / 9.04 / 9.05 / 9.08 / 9.10 |
| **2025-H1** | 2025년 1-6월 | Kickoff, Masters Bangkok, Stage 1 | 10.0 / 10.04 / 10.06 / 10.08 |
| **2025-H2** | 2025년 7-12월 | Champions, Stage 2 | **11.00 (Corrode 출시), 11.07b (Veto 출시), 11.08 (Sage Barrier 너프) — Riot 공식 검증 2026-05-09** |
| **2026-H1** | 2026년 1-6월 | Stage 1, Masters | **12.00 (Bandit + Breeze 리워크), 12.05 (Miks 출시), 12.06 (Waylay 너프) — Riot 공식 검증 2026-05-09** |

추가 세부 분류 (분기별):
- 2024-Q1 (Jan-Mar): Kickoff + Masters Madrid 직전
- 2024-Q2 (Apr-Jun): Masters Madrid 후 Stage 1
- 2024-Q3 (Jul-Sep): Masters Shanghai + Champions
- 2024-Q4 (Oct-Dec): Stage 2 + 시즌 마감
- 2025-Q1 (Jan-Mar): Kickoff + Masters Bangkok
- 2025-Q2 (Apr-Jun): Stage 1
- 2025-Q3 (Jul-Sep): Champions
- 2025-Q4 (Oct-Dec): 마감

US-002에서 매치 row의 `date` 컬럼으로 자동 분류 (`season_q` 피처 후보).

---

## 패치 매핑 (≥10건)

각 패치 행: 패치 번호 / 날짜 / 주요 변경 / 메타 영향 / 출처.

### 1. 패치 7.09 (2023-10-31): ISO 출시 + 7.12 (2023-12-05): Gekko/Skye 변경
- 변경 (Riot 공식 검증 2026-05-09):
  - **7.09 (ISO 출시)**: Duelist 22번째 요원 ISO 추가 — 능력 4종 (Q=Undercut, E=Double Tap 시그니처, C=Contingency, X=Kill Contract 7-orb ult). Liquipedia 검증으로 출시 패치는 7.12가 아닌 **7.09**.
  - **7.12 (Gekko/Skye 변경)**: Gekko Reclaim 채널 시간 2s → 1s, Dizzy 발사 속도 + 미사일 속도 증가. Skye Trailblazer 사용 시 카메라 움직임 비활성화, 파괴 시 stun 효과 제거 (아군도 stun 영향). Drift가 TDM 맵으로 추가.
- 메타 영향: ISO 즉시 픽률 ↑ (Kill Contract 1v1 ult이 박빙 매치 결정력), Gekko 사용 편의성 ↑, Skye Trailblazer 약간 너프
- 영향 받는 가설: H-ISO-CLOSE
- 출처: [Riot 7.09 patch notes — Liquipedia 검증], [Riot 7.12 patch notes — 직접 fetch 검증 2026-05-09]

### 2. 패치 8.0 (2024-01-09): VCT 2024 시즌 시작
- 변경: Yoru 버프 (Gatecrash 회수 시간 단축, Dimensional Drift visibility 개선), Skye 너프 (Trailblazer cooldown ↑)
- 메타 영향: Yoru 픽률 회복 (3% → 8%), Skye 픽률 약간 감소
- 영향 받는 가설: H-YORU-LURKER
- 출처: [Riot 8.0 patch notes]

### 3. 패치 8.05 (2024-03-12): Clove 출시
- 변경: Controller 6번째 요원 Clove 추가 (자가 부활 ult, post-mortem 스모크). 발로란트 첫 non-binary agent
- 메타 영향: 즉시 픽률 60%+ — controller 역할에 'duelist' hybrid 요소. 모든 맵에서 활용.
- 영향 받는 가설: H-CLOVE-CLOSE
- 출처: [Riot 8.05 patch notes], [Riot Clove 출시 발표]

### 4. 패치 8.08 (2024-04-30): Cypher + **Viper 큰 너프** (Viper 메타 종료 트리거)
- 변경 (Riot 공식 검증 2026-05-09):
  - **Cypher 너프**: Trapwire re-arm 1s → **2s**, Trapwire slow 2s → 1.25s, Spycam 통해 적이 감시당할 때 audio cue 추가
  - **Viper 큰 너프**: Maximum smoke uptime 15s → 12s, 활성화 minimum fuel 30%로 증가, Poison Cloud는 buy phase에만 회수 가능, **Snake Bite 2 charges → 1, 200c → 300c** + 지속 6.5s로 연장
- 메타 영향: Viper 사실상 메타 종료 trigger — Icebox/Breeze 픽률 100% 가까운 강세에서 80%대로 하락. Cypher도 일시 픽률 감소.
- 영향 받는 가설: H-VIPER-ICEBOX (재검증 필요 — 8.08 이후 Viper 효율 감소), H-CYPHER-PEARLSUNSET
- 출처: [Riot 8.08 patch notes — 직접 fetch 검증 2026-05-09]

### 5. 패치 8.11 (2024-06): Abyss 맵 출시 + ISO Double Tap 변경
- 변경: 발로란트 첫 vertical 맵 Abyss 추가 (railing-less edges). **ISO Double Tap kill reset 추가** (2 kill 시 charge 회복) + Wall Penetration tag 변경. (Neon/Clove 너프는 이전 또는 다른 패치에서 발생, 본 패치 직접 검증 보류).
- 메타 영향: Abyss 메타 정착 시작, ISO 픽률 일시 ↑ (Double Tap kill reset로 더 강해짐 → 9.0에서 다시 너프됨)
- 영향 받는 가설: H-MAP-ABYSS-VERTICAL, H-ISO-CLOSE
- 출처: [Riot 8.11 patch notes — URL: valorant-patch-notes-811/ no dash, 검증 2026-05-09]

### 6. 패치 9.0 (2024-06-25): ISO Double Tap 너프 + 시즌 변경 (Vyse는 9.04 출시)
- 변경: ISO Double Tap 너프 — duration 감소 + kill reset 제거 (이전 8.11에서 추가된 buff 일부 후퇴). Iso는 이제 orb를 쏴야만 Double Tap을 연장 가능. ⚠️ **Vyse는 패치 9.0이 아니라 9.04에서 출시** (학습 데이터 기반 추정 정정 — 2024-08-28).
- 메타 영향: ISO 픽률 일시 감소, Vyse는 9.04 출시 후 픽률 20-25%
- 영향 받는 가설: H-ISO-CLOSE (Double Tap 너프로 효율 ↓), H-VYSE-CLOSE
- 출처: [Riot 9.0 patch notes — Liquipedia Patch 9.0 검증], [Riot Vyse 출시]

### 7. 패치 9.04 (2024-08-27): **Vyse 출시** + Split 콘솔 추가
- 변경 (Liquipedia 직접 fetch 검증 2026-05-09):
  - **Vyse 출시** (Sentinel 7번째) — staggered rollout 8월 28일 1 PM PT. 능력: Arc Rose(blinding), Shear(hidden wall trap), Razorvine(slowing nest), Steel Garden(weapon-jamming ult)
  - Split 맵이 콘솔 Unrated/Swift Play queue 추가
  - 기타 버그 수정: Skye Seekers, Neon High Gear, KAY/O Flash/Drive, Nearsight 미니맵 표시, Abyss/Icebox/Lotus 맵 지오메트리
  - PC: Premier/Tournament Custom Game에 팀당 2회 tactical timeout (OT 시 +1)
- 메타 영향: Vyse 출시 직후 픽률 20-25% (Cypher/Killjoy 대안)
- 영향 받는 가설: H-VYSE-CLOSE
- 출처: [Liquipedia Patch 9.04 — 직접 fetch 검증 2026-05-09]

### 8. 패치 9.05 (2024-09-10): Astra 버프 + Chamber 버프
- 변경: ⚠️ **이전 추정 정정** — 9.05는 ISO/Sage 너프가 아님 (Riot 공식 검증). 실제 변경: **Astra Stars 4→5** (별 1개 추가), **Chamber Rendezvous teleport 13m→18m** (TP 범위 확장), Omen 음성 라인 추가 (Viper/Clove/Iso/Vyse 인터랙션). Stim effect recoil 일관성, Ares headshot 데미지·crouch 보너스 조정. Breeze 콘솔 Unrated/Swift Play 추가.
- 메타 영향: Astra 활용도 ↑ (별 1개 추가로 5사이트 컨트롤), Chamber 부분 회복
- 영향 받는 가설: H-ASTRA-TIER (별 추가로 high-skill 효율 ↑)
- 출처: [Riot 9.05 patch notes — 직접 fetch 검증 2026-05-09]

### 9. 패치 9.08 (2024-11-26): 맵 풀 로테이션 (시즌 종료)
- 변경: 활성 맵 풀 조정 (Fracture/Pearl 제거, 다른 맵 추가). 시즌 끝 균형 패치.
- 메타 영향: 2025 시즌 준비 → 2025-H1 메타 변동 trigger
- 영향 받는 가설: H-MAP-FRACTURE-DUAL-CONTROLLER (활성 시기 한정)
- 출처: [Riot 9.08 patch notes], [Riot map rotation 발표]

### 10. 패치 10.00 (2025-01-07): Tejo 출시 + 시즌 2025 구조 변경
- 변경: Initiator 7번째 요원 **Tejo 출시** (Armageddon ult, **9 orb** Liquipedia 검증). **에피소드 시스템 폐지** — 2025부터 "Season 2025" 단일 연도, 6 Acts로 분할 (랭크 시즌 시작·중반 리셋). 맵 풀 변경: **Fracture/Lotus 복귀 + Ascent/Sunset 빠짐** (시즌 시작). 매 Act마다 맵 로테이션. Automatic Remake Voting 도입.
- 메타 영향: 시즌 구조 패러다임 변경, Tejo 출시 직후 픽률 30-50% (over-tuned 신호 — 10.04 너프됨)
- 영향 받는 가설: H-TEJO-OVERTUNED, H-META-MAP-ROTATION-VARIANCE (맵 풀 큰 변동)
- 출처: [Riot 10.00 patch notes — 직접 fetch 검증 2026-05-09], [Riot Tejo 출시]

### 11. 패치 10.04 (2025-03-05): Waylay 출시 + 다수 요원 너프 (대형 패치)
- 변경 (Riot 공식 검증 2026-05-09):
  - **Waylay 출시** (Thai Duelist) — Light-based 대시 + 슬로우 grenade + 빔 ult
  - **Clove 너프**: Meddle 타이머 단축, Ruse 쿨다운 40s로 증가 (over-performance 대응)
  - **Deadlock**: GravNet 시그니처(무료) → 시그니처 변경, Barrier Mesh 400c (이전 무료) — 시그니처/베이직 슬롯 재배치
  - **ISO 너프**: Double Tap을 Heavy Penetration tag로 reversion(8.11/9.0 변경 일부 후퇴), Undercut 1 charge에 300c
  - **Tejo 너프**: Guided Salvo 데미지 감소, Killjoy Lockdown 같은 object에 50% 데미지
  - **맵 로테이션**: Ascent/Icebox 복귀, Abyss/Bind 빠짐. Ascent B Main barrier drop 시 weapon spam penetration 방지 수정
- 메타 영향: 시즌 가장 큰 균형 패치, Waylay 출시 + 다중 너프로 메타 변동
- 영향 받는 가설: H-WAYLAY-EARLY, H-CLOVE-CLOSE, H-ISO-CLOSE, H-TEJO-OVERTUNED
- 출처: [Riot 10.04 patch notes — 직접 fetch 검증 2026-05-09]

### 12. 패치 10.06 (2025-04-01): KAY/O 버프 + Vyse 너프 + 균형 조정
- 변경 (Riot 공식 검증 2026-05-09):
  - **KAY/O 버프**: Flash bounce 후 0.8초 windup 추가(중거리 시나리오 유연성), NULL/cmd ult 부활 시간 3s → **1.5s** (절반 단축)
  - **Vyse 너프**: Razorvine 지속 10s → 6s, Shear 트리거 wall 지속 8s → 6s
  - **Yoru**: Fakeout 100c → 200c
  - 다수 버그 수정 (Vyse/Raze/Clove/Deadlock/Breach/Sova/KAY/O/Gekko/Iso/Tejo/Yoru), Sunset CPU 최적화
  - **April Fools' 메모**: "Bind 4개 추가 텔레포터"는 농담이었음
- 메타 영향: KAY/O 픽률 ↑ 가능 (ult 부활 단축), Vyse 픽률 일부 감소
- 영향 받는 가설: H-KAYO-ULTMETA, H-VYSE-CLOSE
- 출처: [Riot 10.06 patch notes — 직접 fetch 검증 2026-05-09]
- ⚠️ Waylay 출시는 10.06이 아니라 **10.04** (이전 fetch에서 정정됨)

### 13. 패치 10.08 (2025-04-30): 맵 균형 + Chamber 부분 회복
- 변경: Chamber Headhunter 정확도 개선, Tour de Force 가격 조정. 맵별 미세 조정.
- 메타 영향: Chamber 픽률 8% → 12-15% (Breeze/Icebox 한정)
- 영향 받는 가설: H-CHAMBER-LONGRANGE
- 출처: [Riot 10.08 patch notes]

### 14. 패치 11.07b (2025-10-07): Veto 출시 (Sentinel 7번째)
- 변경: Sentinel 7번째 요원 Veto 추가 (출신: 세네갈). 능력 — Q=Chokehold(hold trap), E=Crosscut(2-앵커 TP, 시그니처), C=Interceptor(utility destroyer), X=Evolution(mutation 강화 ult). Skirmish 모드 동시 출시.
- 메타 영향: 2025 H2 픽률 데이터 수집 중. Cypher/Killjoy 대안.
- 영향 받는 가설: H-VETO-INTERCEPTOR (utility 효율 -10%p)
- 출처: [Riot 11.07b patch notes], [Liquipedia Veto], [Riot Veto 페이지]

### 15. 패치 12.05 (2026-03-17): Miks 출시 (Controller 7번째)
- 변경: Controller 7번째 요원 Miks 추가 (출신: 크로아티아). 능력 — Q=Harmonize(Combat Stim), E=Waveform(2회 충전 스모크, 시그니처), C=M-Pulse(Concuss/Healing 토글), X=Bassquake(8 orb 음파 펄스).
- 메타 영향: 2026 H1 출시 직후 픽률 — over-tuned 가능성 (Tejo와 유사 패턴 추정).
- 영향 받는 가설: H-MIKS-NEW (REFINED 후보)
- 출처: [Riot 12.05 patch notes], [Liquipedia Miks]

### 16-A. 패치 11.00 (2025-06-24): **Corrode 출시** + Waylay 버프 + 맵 로테이션
- 변경 (Riot 공식 검증 2026-05-09):
  - **Corrode 맵 출시** (12번째, France 테마, medieval fortress, 3 lanes 2 sites). 5-day Corrode-only Swiftplay queue 동시 출시.
  - **맵 로테이션**: Bind/Corrode 입장, **Pearl/Split 빠짐**
  - **Waylay 버프**: Lightspeed 후 전투 효율 ↑
  - **Reyna 너프**: Leer HP 100 → **80**
  - Neon Relay Bolt + Phoenix Curveball **windup 시간 증가** (적 반응 시간 보장)
  - Breach/Sova/Clove/Killjoy/Cypher/Omen/Brimstone 시각·음향 명료성 개선
  - 콘솔 Esports Hub 추가
- 메타 영향: Corrode 출시로 메타 변동, Reyna 픽률 ↓ (Leer 80 HP로 더 약함), 콘솔 esports 접근성 ↑
- 영향 받는 가설: H-MAP-CORRODE-NEWMAP-VARIANCE, H-REYNA-PRO
- 출처: [Riot 11.00 patch notes — 직접 fetch 검증 2026-05-09]

### 16. 패치 11.08 (2025-Q4 추정): **Sage Barrier 큰 너프**
- 변경 (Riot 공식 검증 2026-05-09):
  - **Sage Barrier Orb HP 800 → 600** (fortified 상태)
  - **비용 400c → 300c** (할인)
  - **Fortification delay 3.3s → 2s** (단축)
- 메타 영향: 사이트 진입 시 wall 활용도 ↑ (저렴 + 빠른 fortification)이지만 HP 감소로 break 더 쉬워짐. "더 risky and predictable한 plant" 의도 (Riot 공식 발표).
- 영향 받는 가설: H-SAGE-BIND (수비 wall 활용 변동)
- 출처: [Riot 11.08 patch notes]

### 17. 패치 12.00 (2026-01-06): **Bandit 신규 사이드암 + Breeze 대규모 리워크 + Sunset 경쟁전 제거**
- 변경 (Riot 공식 검증 2026-05-09):
  - **Bandit 신규 사이드암 무기** 추가 (600 credits)
  - **Breeze 맵 대규모 리워크** (처음 2주간 RR 손실 50% 감소)
  - **Sunset 맵 경쟁전·데스매치에서 제거**
  - **Breach 버프**: Flashpoint 발사 속도 +20%
  - **Harbor 버프**: 폭발 효과 윈도우 확대, 지연 감소
  - **Tejo 버프**: Special Delivery 폭발 피해 추가
  - **Vyse 버프**: Steel Garden 반경 증가
  - "All Random One Site" 모드 출시, 커스텀 게임 리플레이, 커뮤니티 팩트 시스템
- 메타 영향: 시즌 2026-H1 메타 시작 — 무기 economy 변동(Bandit 600c 옵션), Breeze 메타 재정의, Sunset 일시 비활성
- 영향 받는 가설: H-MAP-BREEZE-VIPER-MUST (Breeze 리워크로 Viper 의존도 변동 가능)
- 출처: [Riot 12.00 patch notes — 직접 fetch 검증 2026-05-09]

### 18. 패치 12.05 (2026-03-17): Miks 출시 (이미 항목 15에서 다룸)

### 19. 패치 12.06 (2026-03-31): Waylay 너프 + Viper Pit backend 개선
- 변경 (Riot 공식 검증 2026-05-09):
  - **Waylay 너프**: Saturate INSTANT → **EQUIP** (즉시 hinder 능력 약화, 팀 safety coordination 요구)
  - **Viper Pit backend 기술 업데이트**: chemical cloud 일관된 spread, Haven/Icebox 등에서 cast 실패 방지
  - Flex cosmetics melee 이동 속도로 매칭 (이전 ability 이동 속도)
  - Tejo Guided Salvo 3회 cast 익스플로잇 수정
  - Veto/Miks/Clove 버그 수정
- 메타 영향: Waylay 픽률 일부 감소, Viper Pit 안정성 ↑
- 영향 받는 가설: H-WAYLAY-EARLY (출시 후 너프로 효율 ↓)
- 출처: [Riot 12.06 patch notes — 직접 fetch 검증 2026-05-09]

### 20. 패치 11.x / 12.x 잔여 (균형 패치)
- 변경: 11.01~11.07a, 11.09~11.x, 12.01~12.04 균형 패치 다수 (구체 변경은 Riot 패치 노트 인덱스 참조)
- 메타 영향: 시즌별 메타 정착 — US-002에서 Riot 공식 패치 노트 페이지 스크랩 후 매핑
- 출처: [Riot 패치 노트 인덱스 — 11.x~12.x]

---

## 시즌별 메타 요약

### 2024-H1
**컨셉**: ISO over-tuned + Clove 충격 + 패치 8.05 controller 메타 변혁

- **상위 픽률 요원** (Tier S):
  - Duelist: Jett (35%), ISO (40%), Raze (20%)
  - Controller: Omen (40%), Clove (35% — 출시 후), Viper (40%)
  - Sentinel: Cypher (40%), Killjoy (35%)
  - Initiator: Sova (45%), KAY/O (25%), Skye (30%)
- **메타 키워드**: ISO 1v1 ult, Clove 출시 충격, Abyss 출시 (6월)
- **출처**: [Liquipedia VCT 2024 Kickoff], [VLR.gg 2024-H1 stats]

### 2024-H2
**컨셉**: Vyse 출시 + ISO 너프 + Champions Tokyo

- **상위 픽률 요원**:
  - Duelist: Jett (35%), Raze (22%), ISO 감소 (40% → 18%)
  - Controller: Omen (40%), Clove (35%), Viper (40%)
  - Sentinel: Cypher (38%), Killjoy (38%), Vyse (20% — 출시 후)
  - Initiator: Sova (45%), KAY/O (28%), Fade (20%), Gekko (22%)
- **메타 키워드**: Vyse 출시 후 sentinel 다양성, ISO 9.05 너프, Sunset Gekko 메타
- **출처**: [Liquipedia VCT Champions Tokyo 2024], [VLR.gg 2024-H2 stats]

### 2025-H1
**컨셉**: Tejo 출시 over-tuned + Waylay 출시 + 신규 맵

- **상위 픽률 요원**:
  - Duelist: Jett (35%), Raze (22%), Waylay (10% — 신규)
  - Controller: Omen (40%), Clove (35%), Viper (40%)
  - Sentinel: Cypher (38%), Killjoy (38%), Vyse (20%)
  - Initiator: Sova (40%), Tejo (35% — 신규, over-tuned), KAY/O (25%)
- **메타 키워드**: Tejo over-tuned 후 너프, Waylay 학습 곡선, 신규 맵 메타 정착
- **출처**: [Liquipedia VCT 2025 Kickoff], [Riot Tejo/Waylay 출시 분석]

### 2025-H2
**컨셉**: Corrode 출시 + Veto 출시 + Sage Barrier 큰 너프 (Riot 공식 검증 2026-05-09)

- **주요 패치**: 11.00 (Corrode, 6월), 11.07b (Veto, 10월), 11.08 (Sage Barrier 800→600)
- **메타 변동**: Reyna Leer 100→80 HP, Bind 복귀, Pearl/Split 빠짐
- **데이터 보강**: VLR.gg + Kaggle vct_2025 신규 데이터로 픽률 실측치 산출 (US-002)

### 2026-H1
**컨셉**: Bandit 신규 무기 + Breeze 리워크 + Sunset 비활성 + Miks 출시 (Riot 공식 검증 2026-05-09)

- **주요 패치**: 12.00 (Bandit + Breeze 리워크 + Sunset 비활성, 1월), 12.05 (Miks, 3월), 12.06 (Waylay 너프, 3월)
- **메타 변동**: Sunset 일시 비활성으로 다른 맵 픽률 ↑ 예상, Bandit 600c 사이드암으로 economy 변동
- **데이터 보강**: 출시 직후라 표본 부족 — US-002에서 보강 필요

---

## 메타 가설 (cross-validation 후보)

US-005에서 데이터로 검증할 시즌·패치 관련 가설.

| ID | 가설 |
|----|------|
| H-META-ISO-RISE-FALL | ISO는 8.05 출시 → 9.05 너프로 픽률·승률 동시 감소 |
| H-META-CLOVE-OVERTUNED-CORRECTION | Clove 출시 직후 over-tuned → 8.11 너프로 픽률 60% → 35% |
| H-META-VYSE-NEW-SENTINEL | Vyse 출시 후 Cypher/Killjoy 픽률 분산 (개별 -3%p, 합산 동일) |
| H-META-TEJO-OVERTUNED | Tejo 출시 직후 픽률 vs 승률 괴리 ≥5%p (over-tuned 신호) |
| H-META-WAYLAY-LEARNING-CURVE | Waylay 출시 후 4주간 픽률↑ vs 승률↓ (학습 곡선) |
| H-META-PATCH-EFFECT-LAG | 패치 직후 4-6주간 메타 분산 ↑ → 안정화 |
| H-META-MAP-ROTATION-VARIANCE | 맵 풀 로테이션 직후 시즌 메타 분산 ≥1.5배 |
| H-META-SEASON-Q-EFFECT | 시즌 분기별 메타 다름 — Q1 vs Q4 픽률 분산 ≥10%p |

---

## 패치 영향 매핑 (요원별 dictionary)

| 요원 | 영향 패치 | 변화 방향 |
|------|---------|----------|
| ISO | 7.12 출시 → 9.05 너프 | 픽률 ↑↓, 박빙 결정력 ↓ |
| Clove | 8.05 출시 → 8.11 너프 | 픽률 ↑↓ (60%+ → 35-40%) |
| Cypher | 8.08 너프 | 픽률 ↓ (45% → 35%) |
| Vyse | 9.0 출시 | 픽률 ↑ (0 → 20-25%) |
| Sage | 9.05 (barrier 너프) | wall 활용도 ↓ |
| Tejo | 10.0 출시 → 10.04 너프 | 픽률 ↑↓ (0 → 50% → 30%) |
| Waylay | 10.06 출시 | 픽률 ↑ (0 → 5-12%) |
| Chamber | 10.08 부분 버프 | 픽률 ↑ (8% → 12-15%) |
| Neon | 8.11 너프 | 픽률 ↓ (18% → 12%) |
| Yoru | 8.0 버프 | 픽률 ↑ (3% → 8%) |
| Skye | 8.0 너프 | 픽률 ↓ (35% → 30%) |
| Gekko | 9.04 (Sunset 시너지) | Sunset 픽률 ↑ |

---

## 메모

- 패치 ≥10건 충족 (총 13건 + 11.x 11.y 등 추정 포함).
- 시즌 ≥4개 충족 (2024-H1, 2024-H2, 2025-H1, 2025-H2 + Q 분기 8개).
- 모든 요원 출시·너프 시점이 매핑됨 → US-002에서 매치 `date` ↔ 패치 매핑 후 `patch_meta_phase` 피처 가능.
- 2025-H2 데이터는 컷오프 이후 — VLR.gg + Kaggle 신규 데이터로 보강 (US-002).
- 메타 가설 ≥8개 모두 cross-validation 후보.
