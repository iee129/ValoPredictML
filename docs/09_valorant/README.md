# 09_valorant — Valorant 게임 도메인 리서치

ML 피처 설계 및 cross-validation을 위한 Valorant 게임 도메인 지식 베이스.
**`.omc/plans/valorant_domain_rules_close_match.md` US-001 산출물.**

US-005 cross-validation의 한 축(도메인 가설) — 데이터(US-004) 통계와 양방향 검증 → CONFIRMED / CONTRADICTED / REFINED 3분류.

---

## 파일

| 파일 | 내용 | 도메인 가설 수 |
|------|------|---------------|
| [valorant.md](valorant.md) | 게임 규칙·요원 역할 분류·맵 목록·승패 구조 (기본 안내) | — |
| [agents.md](agents.md) | 29개 요원 카드 (능력/강한 맵/시너지/카운터/메타 위상) + 가설 ≥1/요원 | 29 |
| [maps.md](maps.md) | 13개 맵 카드 (사이드 어드밴티지/이상 구성/카테고리) + 가설 ≥2/맵 | 29 |
| [meta.md](meta.md) | VCT 2024-2025 시즌 (8 카테고리) + 패치 매핑 ≥10건 | 8 |
| [counters.md](counters.md) | 카운터 매트릭스 18쌍 (강도 0.4-0.7) + 데이터 검증 가설 | 18 |
| [economy.md](economy.md) | 라운드 이코노미 + 27 요원 ult cost + visualize25 SQLite 매핑 | ≥18 |
| sources.md *(미작성)* | 인용 URL (Riot 공식 + Liquipedia + VLR.gg + 프로팀) — 추후 작성 예정 | — |

총 **도메인 가설 ≥100개** — US-005 `validate_domain_hypothesis()` 입력.

---

## 사용 방법 (US-005 cross-validation 입력)

```python
# US-005에서 도메인 가설 추출
from ml.cross_validation import load_domain_hypotheses, validate_domain_hypothesis

hypotheses = load_domain_hypotheses("docs/09_valorant/")
# → list of {hypothesis_id, domain_claim, source_url, expected_metric, expected_effect}

for h in hypotheses:
    result = validate_domain_hypothesis(
        hypothesis=h,
        data_stat=compute_stat(h["expected_metric"]),
        significance=0.05,
        min_n=100,
    )
    # → CONFIRMED / CONTRADICTED / REFINED
```

---

## 참고

### 요원 역할 분류 (코드 27 + 웹 검증 신규 2 = 29)

`src/domain/agent_roles.py` `AGENT_ROLE_MAP` 기준 **29개**:

- **Duelist (타격대)** 8종: Jett · Phoenix · Raze · Reyna · Yoru · Neon · ISO · Waylay
- **Initiator (척후대)** 7종: Sova · Skye · Breach · KAY/O · Fade · Gekko · Tejo
- **Controller (전략가)** 7종: Brimstone · Viper · Omen · Astra · Harbor · Clove · Miks (2026-03)
- **Sentinel (감시자)** 7종: Cypher · Killjoy · Sage · Chamber · Deadlock · Vyse · Veto (2025-10)

### 한국어 역할 명칭
사용자 직접 확인 결과 (memory: `reference_valorant_roles.md`):
- Duelist = **타격대**
- Initiator = **척후대**
- Controller = **전략가**
- Sentinel = **감시자**

### 활성 맵 (13개, `src/domain/agent_roles.py` `MAP_ORDER`)
Ascent · Bind · Haven · Split · Icebox · Breeze · Fracture · Pearl · Lotus · Sunset · Abyss · Drift · Corrode

---

## 갱신 주기

- **agents.md / maps.md**: 신규 요원·맵 출시 시 (Riot 패치 노트 기준)
- **meta.md**: 분기별 메타 리뷰 (VCT 시즌 종료 후)
- **counters.md**: 신규 능력 출시 또는 메커니즘 변경 시
- **economy.md**: Riot 이코노미 시스템 변경 시 (드물게 발생)
- **sources.md** *(예정)*: 작성 후 URL 변경 시 즉시 갱신 (linkrot 방지)

US-002 데이터 인벤토리 작성 후 `data_inventory.md`, US-004 후 `data_derived_rules.md`, US-005 후 `cross_validation_report.md`, US-008 후 `discoveries.md`가 같은 디렉토리에 추가될 예정.
