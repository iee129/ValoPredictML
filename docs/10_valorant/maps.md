# maps.md — 발로란트 맵 도메인 카드

작성: 2026-05-09
출처 정책: 사이드 어드밴티지 수치는 **VCT 2024-2025 추정 범위**, US-002/US-004에서 vct_2021_2023 + visualize25 SQLite + VLR.gg 데이터로 정확한 수치 산출 예정.

`ml/agent_roles.py`의 `MAP_ORDER` 기준 12개 맵 + 2025년 신규 맵(Corrode) 포함. 활성 경쟁 풀(active competitive pool)은 시즌마다 7-9개로 로테이션됨.

---

## 맵 카드 형식

```
## 맵명
- 사이트 수 / 특수 구조: ...
- 사이드 어드밴티지 (수비 vs 어택): ...% (출처)
- 이상 구성 (프로 메타): ...
- 키 픽 / 권장 요원: ...
- 약한 요원: ...
- 도메인 가설 ≥2 (cross-validation 후보): ...
- 출처: ...
```

---

## 출처 라벨 → sources.md anchor 매핑

본 문서에서 사용되는 출처 라벨이 `sources.md` S-N 번호로 추적된다.

| 인라인 라벨 | sources.md anchor | URL |
|------------|-------------------|-----|
| `[Riot {맵} 페이지]`, `[Riot Maps Page]` | [S-3] | https://playvalorant.com/en-us/maps/ |
| `[Liquipedia {맵}]`, `[Liquipedia Maps]` | [S-23] | https://liquipedia.net/valorant/Maps |
| `[VLR.gg {맵} stats]`, `[VCT 2024 {맵} 통계 — VLR.gg]` | [S-26]+[S-16] | VLR.gg agent stats × VCT 2024 |
| `[VCT 2024 {맵}]` | [S-16] | https://liquipedia.net/valorant/Valorant_Champions_Tour/2024 |
| `[Riot Icebox 리워크 패치 7.05]` | [S-1] 인덱스 통해 7.05 | Patch Notes Index |
| `[Riot 8.11 Abyss 출시]` | [S-9] | https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-8-11/ |
| `[VCT 2024 Champions Abyss 통계]` | [S-18] | https://liquipedia.net/valorant/Valorant_Champions/2024 |
| `[Riot Corrode 출시 발표 2025]` | [S-1] 인덱스 통해 | Patch Notes Index |

---

## Ascent
- 사이트 수 / 특수 구조: 2 사이트 (A, B), 가운데(Mid) 컨트롤 중요, 메카닉 도어 시스템 (B 사이트 컷-오프 도어)
- 사이드 어드밴티지: **약간 어택 유리 (어택 ~50.5-51.5%)** — VCT 2024 통계 기준
- 이상 구성 (프로 메타):
  - Controller: **Omen** (Mid TP 활용, 픽률 70%+) 또는 Astra
  - Sentinel: **Killjoy** (사이트 락) 또는 Cypher
  - Initiator: **Sova** (Mid 정찰 화살) + KAY/O
  - Duelist: **Jett** 또는 Raze
- 키 픽: Omen, Sova, Killjoy, Jett, KAY/O (전형적 5-pillar)
- 약한 요원: Brimstone (Mid 거리 부족), Phoenix (오픈 맵)
- 도메인 가설:
  - **H-MAP-ASCENT-OMEN-MUST**: "Ascent에서 Omen 부재 시 어택 라운드 승률 -5%p"
  - **H-MAP-ASCENT-MID-CONTROL**: "Ascent에서 Mid 컨트롤 점유 팀의 라운드 승률 +12%p"
- 출처: [VCT 2024 Ascent 통계 — VLR.gg], [Liquipedia Ascent], [Riot Ascent 페이지]

## Bind
- 사이트 수 / 특수 구조: 2 사이트 (A, B), **2개 일방 텔레포터** (A Short ↔ B Long), Mid 없음
- 사이드 어드밴티지: **시즌별 변동** — 2022 어택 52.0% / 2024 어택 53.6% / **2025 어택 45.9%** (2025에 수비 강세 회귀) — Liquipedia VCT Champions Statistics 검증
- 이상 구성:
  - Controller: **Brimstone** (즉발 스모크) 또는 Viper, Harbor
  - Sentinel: **Cypher** (TP 트랩) 또는 Vyse
  - Initiator: **Skye** + Breach (좁은 통로)
  - Duelist: **Raze** (분열탄 효율) 또는 Jett
- 키 픽: Brimstone, Cypher, Skye, Raze, Breach
- 약한 요원: Sova (오픈 라인 부족), Chamber (장거리 부족)
- 도메인 가설:
  - **H-MAP-BIND-CONTROLLER-2**: "Bind에서 controller ≥2명(Brimstone+Viper or Brim+Harbor) 시 어택 승률 +6%p"
  - **H-MAP-BIND-RAZE**: "Bind에서 Raze 보유 팀 박빙 라운드 승률 +3%p (Jett 대비)"
  - **H-MAP-BIND-DEFENDER**: "Bind는 TP 구조로 수비 유리 — 수비 사이드 ≥52%"
- 출처: [VCT 2024 Bind — VLR.gg], [Liquipedia Bind], [Riot Bind]

## Haven
- 사이트 수 / 특수 구조: **3 사이트 (A, B, C)** — 발로란트 유일한 3-사이트 맵 (mid 파괴 가능 패널 400 HP)
- 사이드 어드밴티지: **시즌별 큰 변동** — 2022 어택 48.1% / 2024 47.5% / **2025 어택 57.7%** (2025 메타에서 어택 강세 급등) — Liquipedia VCT Champions Statistics 검증
- 이상 구성:
  - Controller: **Omen** (장거리 스모크) 또는 Astra
  - Sentinel: **Killjoy** 또는 Cypher
  - Initiator: **Sova** + Skye (3 사이트 정보 필수)
  - Duelist: **Jett** (수직 이동) 또는 Phoenix
- 키 픽: Omen/Astra, Sova, Skye, Killjoy, Jett
- 약한 요원: Brimstone (3 사이트 + 거리), Chamber (장거리 부족), Yoru
- 도메인 가설:
  - **H-MAP-HAVEN-DOUBLE-INITIATOR**: "Haven에서 initiator ≥2명 시 정보 우위로 어택 승률 +5%p"
  - **H-MAP-HAVEN-3-SITE-ROT**: "Haven은 3 사이트로 수비 회전 부담 — sentinel ≥1 + 빠른 정보 필수"
- 출처: [VCT 2024 Haven], [Liquipedia Haven]

## Split
- 사이트 수 / 특수 구조: 2 사이트 (A, B), **수직 통로(밧줄·지하)**, Mid 좁음
- 사이드 어드밴티지: **수비 유리 (수비 ~52-54%)** — 좁은 통로로 수비 우위
- 이상 구성:
  - Controller: **Omen** 또는 Brimstone
  - Sentinel: **Cypher** 또는 Sage (벽으로 통로 차단)
  - Initiator: **Skye** + Breach
  - Duelist: **Raze** 또는 Jett (수직 이동)
- 키 픽: Omen, Cypher, Skye, Raze/Jett, Breach
- 약한 요원: Sova (수직 라인 제한), Chamber
- 도메인 가설:
  - **H-MAP-SPLIT-DEFENDER-WALL**: "Split에서 Sage wall로 통로 차단 시 수비 라운드 승률 +4%p"
  - **H-MAP-SPLIT-DUELIST-VERTICAL**: "Split에서 Jett/Raze 보유 팀 entry 효율 +5%p"
- 출처: [VCT 2024 Split], [Liquipedia Split]

## Icebox
- 사이트 수 / 특수 구조: 2 사이트 (A, B), **수직 zip-line · 박스 더미**
- 사이드 어드밴티지: **약간 어택 유리 (어택 ~51%)** — 2024 리워크 후 균형
- 이상 구성:
  - Controller: **Viper** (장거리 가스 벽 사실상 필수)
  - Sentinel: **Killjoy** 또는 Sage (B 사이트 락)
  - Initiator: **Sova** (정찰 화살) + KAY/O
  - Duelist: **Jett** (수직 이동) 또는 Neon
- 키 픽: Viper, Killjoy, Sova, Jett, KAY/O
- 약한 요원: Brimstone (장거리 부족), Phoenix
- 도메인 가설:
  - **H-MAP-ICEBOX-VIPER-MUST**: "Icebox에서 Viper 부재 시 어택 라운드 승률 -8%p"
  - **H-MAP-ICEBOX-NEON**: "Icebox에서 Neon 보유 시 entry 효율 Jett 대비 +3%p (긴 통로)"
- 출처: [VCT 2024 Icebox], [Riot Icebox 리워크 패치 7.05]

## Breeze
- 사이트 수 / 특수 구조: 2 사이트 (A, B), **매우 넓은 오픈 라인** + 텔레포터 1개
- 사이드 어드밴티지: **어택 유리 (어택 ~52-53%)** — 어택의 거리 우위
- 이상 구성:
  - Controller: **Viper** (긴 가스 벽 필수) + Brimstone/Harbor
  - Sentinel: **Cypher** 또는 Chamber (long-range)
  - Initiator: **Sova** (긴 정찰 화살)
  - Duelist: **Jett** 또는 Neon (긴 거리 회전)
- 키 픽: Viper, Sova, Cypher/Chamber, Jett, KAY/O
- 약한 요원: Brimstone single (거리 부족), Phoenix, Reyna
- 도메인 가설:
  - **H-MAP-BREEZE-VIPER-MUST**: "Breeze에서 Viper 부재 시 어택 라운드 승률 -10%p (가장 강한 의존)"
  - **H-MAP-BREEZE-LONG-RANGE-SENT**: "Breeze에서 Chamber 픽률 ≥15% (long-range 한정 활용)"
  - **H-MAP-BREEZE-ATTACKER**: "Breeze는 어택 유리 — 어택 사이드 ≥52%"
- 출처: [VCT 2024 Breeze], [Liquipedia Breeze]

## Fracture
- 사이트 수 / 특수 구조: 2 사이트 (A, B), **양방향 어택 스폰(H-shaped)** — 어택이 양쪽에서 동시 진입 가능, zip-line
- 사이드 어드밴티지: **어택 유리 (어택 ~52%)** — 양방향 스폰으로 수비 분산 강제
- 이상 구성:
  - Controller: **Brimstone** + Viper (double controller)
  - Sentinel: **Killjoy** (양쪽 동시 락 어려움)
  - Initiator: **Breach** (스턴) + Sova
  - Duelist: **Neon** 또는 Raze (회전 압박)
- 키 픽: Brimstone, Viper, Killjoy, Breach, Neon
- 약한 요원: 1 controller로는 부족, Cypher (양쪽 cam 한계)
- 도메인 가설:
  - **H-MAP-FRACTURE-DUAL-CONTROLLER**: "Fracture에서 double controller 조합 시 어택 라운드 승률 +5%p"
  - **H-MAP-FRACTURE-SPLIT-PUSH**: "Fracture는 양쪽 동시 압박 시 수비 utility 분산 — 어택 entry +6%p"
- 출처: [VCT 2024 Fracture (활성/비활성 시기 표시)], [Liquipedia Fracture]

## Pearl
- 사이트 수 / 특수 구조: 2 사이트 (A, B), **Mid 컨트롤 중심 + 좁은 회전 통로**
- 사이드 어드밴티지: **균형 (~50-51%)** — 양 사이드 비슷
- 이상 구성:
  - Controller: **Astra** (글로벌 컨트롤) 또는 Harbor
  - Sentinel: **Cypher** (트랩으로 회전 차단)
  - Initiator: **Fade** + Breach
  - Duelist: **Neon** 또는 Jett
- 키 픽: Astra/Harbor, Cypher, Fade, Neon, Breach
- 약한 요원: Brimstone (Mid 거리 부족), Phoenix
- 도메인 가설:
  - **H-MAP-PEARL-CYPHER-MUST**: "Pearl에서 Cypher 부재 시 수비 라운드 승률 -6%p"
  - **H-MAP-PEARL-MID-CONTROL**: "Pearl에서 Mid 점유 팀의 라운드 승률 +10%p"
- 출처: [VCT 2024 Pearl], [Liquipedia Pearl]

## Lotus
- 사이트 수 / 특수 구조: **3 사이트 (A, B, C)** + 회전 도어(rotating door) 2개 + 파괴 가능 벽 1개
- 사이드 어드밴티지: **약간 어택 유리 (어택 ~51-52%)** — Haven처럼 3 사이트
- 이상 구성:
  - Controller: **Astra** 또는 Omen (3 사이트 회전)
  - Sentinel: **Killjoy** + Vyse (이중 sentinel)
  - Initiator: **Fade** (3 사이트 동시 정보) + Skye
  - Duelist: **Raze** 또는 Waylay
- 키 픽: Astra/Omen, Killjoy, Fade, Skye, Raze
- 약한 요원: Brimstone (3 사이트 거리), Chamber, Yoru
- 도메인 가설:
  - **H-MAP-LOTUS-FADE-VS-SOVA**: "Lotus에서 Fade 보유 시 Sova 대비 entry 정보 우위 +3%p (3 사이트 동시 정보)"
  - **H-MAP-LOTUS-DOUBLE-SENT**: "Lotus에서 sentinel ≥2명(Killjoy+Vyse 등) 시 수비 승률 +4%p"
- 출처: [VCT 2024 Lotus], [Liquipedia Lotus]

## Sunset
- 사이트 수 / 특수 구조: 2 사이트 (A, B), **Mid 컨트롤 + Market 좁은 통로**
- 사이드 어드밴티지: **2024 어택 53.6% → 2025 어택 39.6%** (2025 메타에서 수비 60.4% 매우 강세!) — Liquipedia VCT Champions Statistics 검증. 학습 데이터 추정(균형 ~50%)과 큰 차이.
- 이상 구성:
  - Controller: **Omen** 또는 Harbor + Brimstone (double)
  - Sentinel: **Cypher** 또는 Vyse
  - Initiator: **Gekko** (Mosh Pit 효율) + KAY/O
  - Duelist: **Raze** (분열탄) 또는 Phoenix
- 키 픽: Omen, Cypher, Gekko, Raze, KAY/O
- 약한 요원: Chamber (long-range 부족)
- 도메인 가설:
  - **H-MAP-SUNSET-CYPHER-MUST**: "Sunset에서 Cypher 부재 시 수비 라운드 승률 -5%p"
  - **H-MAP-SUNSET-GEKKO-EFFECTIVE**: "Sunset에서 Gekko 픽률 ≥20% (Mosh Pit 효율)"
- 출처: [VCT 2024 Sunset], [Liquipedia Sunset]

## Abyss
- 사이트 수 / 특수 구조: 2 사이트 (A, B), **벽 없는 가장자리(railing-less edges)** — 추락 가능, 발로란트 첫 vertical 맵
- 출시: 2024년 6월 (패치 8.11)
- 사이드 어드밴티지: **2024 어택 50.6% → 2025 어택 57.9%** (2025 메타에서 어택 강세 급등) — Liquipedia 검증
- 이상 구성:
  - Controller: **Omen** (smoke entry) 또는 Clove
  - Sentinel: **Killjoy** 또는 Deadlock (낙하 활용 ult)
  - Initiator: **Sova** + Breach (스턴으로 추락 유도)
  - Duelist: **Jett** (수직 이동) 또는 Raze
- 키 픽: Omen, Killjoy, Sova, Jett, Breach
- 약한 요원: Sage (지형 한계), Chamber
- 도메인 가설:
  - **H-MAP-ABYSS-DEADLOCK**: "Abyss에서 Deadlock ult로 추락 강제 시 라운드 승률 +5%p"
  - **H-MAP-ABYSS-VERTICAL**: "Abyss는 vertical 구조로 Jett/Raze 픽률 ≥35% (수직 이동)"
- 출처: [Riot 8.11 Abyss 출시], [VCT 2024 Champions Abyss 통계]

## Corrode
- 사이트 수 / 특수 구조: 2 사이트 (A, B), 2025 신규 맵
- 출시: 2025년 (구체 패치 미확정 — 출시 직후라 데이터 부족)
- ⚠️ **코드 매핑 불일치**: `ml/agent_roles.py`의 `MAP_ORDER`에는 "Drift"로 등록되어 있고 "Corrode"는 미등록 상태. `normalize_map("Corrode")` 호출 시 `-1` 반환됨. US-002에서 두 가지 중 하나로 통일 필요 (Riot 공식 발표 맵 이름 기준). 본 문서에서는 Riot 공식 발표명 "Corrode"를 사용. `agent_roles.py` 동기화는 US-002에서 alias 추가 또는 `MAP_ORDER` 갱신으로 처리.
- 사이드 어드밴티지: **VCT 2025 Champions 어택 51.4% / 수비 48.6%** (148/288 어택 라운드 승) — Liquipedia 검증, 2025 출시 직후 통계
- 이상 구성: 출시 직후 메타 정착 중 — VLR.gg 픽률 데이터로 보강 필요
- 키 픽: TBD
- 도메인 가설:
  - **H-MAP-CORRODE-NEWMAP-VARIANCE**: "Corrode 출시 직후 메타 분산 — 픽률 변동성이 다른 맵 대비 ≥2배"
  - **H-MAP-CORRODE-DATA-PENDING**: "Corrode는 표본 부족 — REFINED 후보 (조건부 룰만 적용)"
- 출처: [Riot Corrode 출시 발표 2025]

---

## 맵 카테고리 (Map Archetype 후보)

US-004의 KMeans 자동 클러스터링 입력 + cross-validation 기준점.

| 카테고리 | 맵 | 특성 | 권장 controller |
|---------|-----|------|----------------|
| **Open / Long-range** | Breeze, Icebox | 긴 시야, 가스 벽 의존 | Viper (필수) |
| **Closed / Tight** | Bind, Split, Pearl, Sunset | 좁은 통로 + 정보전 | Brimstone, Cypher |
| **Multi-site** | Haven, Lotus | 3 사이트 회전 압박 | Astra, Omen |
| **Vertical** | Split, Abyss, Fracture | 수직 이동 + zip-line | Omen (TP), Jett |
| **Mid-control** | Ascent, Pearl, Sunset | Mid 점유가 라운드 결정 | Omen (Mid TP) |
| **Dual-spawn (active 시)** | Fracture | 양방향 어택 스폰 | Brimstone + Viper |

도메인 가설:
- **H-ARCHETYPE-OPEN-VIPER**: "Open/Long-range 맵에서 Viper 부재 시 어택 라운드 승률 -8%p"
- **H-ARCHETYPE-CLOSED-CYPHER**: "Closed/Tight 맵에서 Cypher 부재 시 수비 라운드 승률 -5%p"
- **H-ARCHETYPE-MULTISITE-INFO**: "Multi-site 맵에서 initiator ≥2 시 어택 라운드 승률 +5%p"

---

## 사이드 어드밴티지 요약 표 (Liquipedia 실측치 — 2026-05-09 검증)

VCT Champions 토너먼트별 어택측 승률 — 시즌별 큰 변동 있음 (메타 + 맵 리워크 영향).

| 맵 | 2022 Champions | 2024 Champions | 2025 Champions | 카테고리 |
|----|---------------|---------------|---------------|----------|
| Ascent | 45.8% | 46.0% | 50.2% | Mid-control (어택 점점 강세) |
| Bind | 52.0% | 53.6% | **45.9%** | Closed (2025에 수비 회귀) |
| Haven | 48.1% | 47.5% | **57.7%** | Multi-site (2025 어택 강세) |
| Split | 비활성 | 비활성 | 비활성 | Closed/Vertical (풀 outside) |
| Icebox | 53.5% | 51.3% | 비활성 | Open (어택 약 유리) |
| Breeze | 47.7% | 비활성 | 비활성 | Open (실측 수비 유리) |
| Fracture | 49.0% | 비활성 | 비활성 | Dual-spawn (균형) |
| Pearl | 46.8% | 비활성 | 비활성 | Closed (수비 유리) |
| Lotus | 비활성 | 54.4% | 51.0% | Multi-site (어택 유리) |
| Sunset | 비활성 | 53.6% | **39.6%** | Closed (2025 수비 60% 강세!) |
| Abyss | 비활성 | 50.6% | **57.9%** | Vertical (2025 어택 강세) |
| Corrode | (미출시) | (미출시) | 51.4% | (신규 2025) |

**핵심 발견**:
- **시즌별 변동성 매우 큼** — 같은 맵이 +5-15%p 변동. 단일 시즌 통계 일반화 위험.
- **2025 메타에서 Sunset 수비 60.4%** — 학습 데이터 기반 추정(50%)과 큰 차이.
- **2025 메타에서 Haven/Abyss 어택 57%+** — 수직·다중 사이트 맵에서 어택 우위 강해짐.
- **2024-2025 활성 맵 풀 변동** — Split/Breeze/Fracture/Pearl 등 비활성. US-002에서 시즌별 활성 풀 매핑 필요.

수치는 Liquipedia VCT Champions Statistics 페이지 직접 추출 (sources.md S-15, S-16, S-17, S-18 참조). US-004 `compute_map_side_advantage()`에서 bootstrap CI로 시즌·meta phase 분리 산출 예정.

---

## 도메인 가설 요약 (총 ≥20개)

| ID | 맵 | 가설 |
|----|-----|------|
| H-MAP-ASCENT-OMEN-MUST | Ascent | Omen 부재 시 -5%p |
| H-MAP-ASCENT-MID-CONTROL | Ascent | Mid 점유 +12%p |
| H-MAP-BIND-CONTROLLER-2 | Bind | controller ≥2 +6%p |
| H-MAP-BIND-RAZE | Bind | Raze 박빙 +3%p |
| H-MAP-BIND-DEFENDER | Bind | 수비 ≥52% |
| H-MAP-HAVEN-DOUBLE-INITIATOR | Haven | initiator ≥2 +5%p |
| H-MAP-HAVEN-3-SITE-ROT | Haven | sentinel ≥1 필수 |
| H-MAP-SPLIT-DEFENDER-WALL | Split | Sage wall +4%p |
| H-MAP-SPLIT-DUELIST-VERTICAL | Split | Jett/Raze entry +5%p |
| H-MAP-ICEBOX-VIPER-MUST | Icebox | Viper 부재 -8%p |
| H-MAP-ICEBOX-NEON | Icebox | Neon entry +3%p |
| H-MAP-BREEZE-VIPER-MUST | Breeze | Viper 부재 -10%p |
| H-MAP-BREEZE-LONG-RANGE-SENT | Breeze | Chamber ≥15% |
| H-MAP-BREEZE-ATTACKER | Breeze | 어택 ≥52% |
| H-MAP-FRACTURE-DUAL-CONTROLLER | Fracture | double controller +5%p |
| H-MAP-FRACTURE-SPLIT-PUSH | Fracture | 양쪽 entry +6%p |
| H-MAP-PEARL-CYPHER-MUST | Pearl | Cypher 부재 -6%p |
| H-MAP-PEARL-MID-CONTROL | Pearl | Mid 점유 +10%p |
| H-MAP-LOTUS-FADE-VS-SOVA | Lotus | Fade vs Sova +3%p |
| H-MAP-LOTUS-DOUBLE-SENT | Lotus | sentinel ≥2 +4%p |
| H-MAP-SUNSET-CYPHER-MUST | Sunset | Cypher 부재 -5%p |
| H-MAP-SUNSET-GEKKO-EFFECTIVE | Sunset | Gekko 픽률 ≥20% |
| H-MAP-ABYSS-DEADLOCK | Abyss | Deadlock ult +5%p |
| H-MAP-ABYSS-VERTICAL | Abyss | Jett/Raze ≥35% |
| H-MAP-CORRODE-NEWMAP-VARIANCE | Corrode | 메타 분산 ≥2배 |
| H-MAP-CORRODE-DATA-PENDING | Corrode | REFINED |
| H-ARCHETYPE-OPEN-VIPER | Archetype | Open + Viper 부재 -8%p |
| H-ARCHETYPE-CLOSED-CYPHER | Archetype | Closed + Cypher 부재 -5%p |
| H-ARCHETYPE-MULTISITE-INFO | Archetype | Multi-site + initiator ≥2 +5%p |

총 **29개 가설** (맵당 ≥2개 만족) — US-005 cross-validation 입력.

---

## 메모

- 활성 맵 풀(competitive map pool)은 시즌마다 변동: 2024 H1 (Ascent/Bind/Breeze/Icebox/Lotus/Split/Sunset), 2024 H2 (+Abyss, -X), 2025 H1 (+Corrode, ...).
- US-002에서 시즌별 활성 풀 매핑 후 모델 입력 시 `season` 컬럼과 결합.
- Map archetype 자동 클러스터링(US-004)은 위 카테고리를 ground-truth가 아닌 **검증 대상**으로 사용 — KMeans가 이 분류와 다른 결과를 내면 CONTRADICTED → Discovery 후보.
