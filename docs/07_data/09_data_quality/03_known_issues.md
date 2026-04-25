# 03. 알려진 데이터 이슈

## 1. 이슈 카탈로그

| ID | 이슈 | 영향 | 해결책 | 상태 |
|----|------|------|--------|------|
| I001 | KAY/O 표기 불일치 | 역할군 미매핑 | `normalize_agent_name()` | ✅ 해결됨 |
| I002 | 맵 로테이션 (비활성 맵 데이터) | 미래 예측 노이즈 | 맵 필터링 옵션 | ⚠️ 부분 해결 |
| I003 | Kaggle 데이터 팀명 표준화 부재 | winner 판별 어려움 | match_id 기반 처리 | ✅ 해결됨 |
| I004 | Riot S3 - gameVersion 누락 경기 | 패치 피처 생성 불가 | 0으로 대체 | ⚠️ 부분 해결 |
| I005 | 신규 요원 (Clove, Tejo, Waylay) 구 데이터 없음 | 원-핫 피처 희소 | 패치 필터링 고려 | ⚠️ 모니터링 필요 |
| I006 | HenrikDev API - 요원 ID → 이름 변환 필요 | 원시 데이터 처리 | UUID 매핑 테이블 | ✅ 해결됨 |
| I007 | VLR.gg 스크래핑 - HTML 구조 변경 가능성 | 파서 실패 | 모니터링 + 재파싱 | ⚠️ 주의 필요 |
| I008 | 랭크 매치 vs 프로 경기 데이터 품질 차이 | 노이즈 증가 | 소스 가중치 적용 | ✅ 설계됨 |
| I009 | 맵명과 요원명 충돌 (Lotus) | 매핑 오류 | 명시적 구분 | ✅ 해결됨 |
| I010 | 경기 중복 (여러 소스 동일 경기) | 데이터 편향 | 중복 제거 파이프라인 | ✅ 설계됨 |

---

## 2. 이슈 상세

### I001: KAY/O 표기 불일치 (해결됨)

**원인:** 데이터 소스마다 다른 표기
- Kaggle: `"KAYO"`, `"Kay/O"`, `"kay-o"`
- Riot API: 고유 UUID로 반환 후 이름 변환 시 `"KAY/O"` 또는 `"KAY-O"`
- VLR.gg: `"KAY/O"` (정확) 또는 `"kayo"` (소문자)

**해결책:**
```python
AGENT_NAME_ALIASES = {
    "kayo": "KAY/O",
    "kay/o": "KAY/O",
    "kay-o": "KAY/O",
    "kay_o": "KAY/O",
    "kayo/": "KAY/O",  # 오타
}

def normalize_agent_name(name: str) -> str:
    lower = name.strip().lower().replace("-", "/")
    return AGENT_NAME_ALIASES.get(lower, name.title() if name.title() in VALID_AGENTS else name)
```

---

### I002: 맵 로테이션 이슈 (부분 해결)

**원인:** Valorant는 7~9개 맵이 활성 로테이션에 포함되며 정기적으로 변경됨.

**현재 활성 맵 (2025년 기준):**
```
Ascent, Bind, Haven, Icebox, Pearl, Lotus, Abyss, Split, Sunset
```

**비활성/제거된 맵:**
- `Breeze` — 제거 (2023년 이후 비로테이션)
- `Fracture` — 제거 (2023년 이후 비로테이션)
- `Drift` — 신규 추가 (2025년)

**영향:**
- Breeze/Fracture 데이터는 구 패치에서만 유효
- 미래 승률 예측에 사용 시 적절하지 않음

**권장 처리:**
```python
ACTIVE_MAPS_2025 = {
    "Ascent", "Bind", "Haven", "Icebox", "Pearl",
    "Lotus", "Abyss", "Split", "Sunset", "Drift",
}
RETIRED_MAPS = {"Breeze", "Fracture"}

def filter_retired_maps(df: pd.DataFrame, keep_retired: bool = False) -> pd.DataFrame:
    """비활성 맵 데이터 처리"""
    if not keep_retired:
        before = len(df)
        df = df[df["map"].isin(ACTIVE_MAPS_2025)].reset_index(drop=True)
        removed = before - len(df)
        print(f"[I002] 비활성 맵 데이터 {removed}행 제거")
    return df
```

---

### I004: gameVersion 누락

**원인:** 일부 오래된 Kaggle 데이터 및 VLR.gg 스크래핑 데이터에 버전 정보 없음.

**영향:** `patch_version` 피처를 0으로 대체 → 패치 피처 희소

**처리:**
```python
def fill_missing_patch_version(df: pd.DataFrame) -> pd.DataFrame:
    if "game_version" not in df.columns:
        df["patch_version"] = 0.0
        df["is_clove_era"] = 0
        return df
    
    df["patch_version"] = df["game_version"].apply(patch_to_float)
    df["patch_version"] = df["patch_version"].fillna(0.0)
    
    # 날짜로 추정 (game_version 없지만 날짜 있는 경우)
    if "match_date" in df.columns:
        mask = df["patch_version"] == 0.0
        df.loc[mask, "patch_version"] = df.loc[mask, "match_date"].apply(date_to_approx_patch)
    
    return df

def date_to_approx_patch(date_str: str) -> float:
    """날짜 기반 패치 버전 추정"""
    import datetime
    try:
        date = pd.to_datetime(date_str)
        # 주요 패치 출시일 기반 추정 테이블
        PATCH_DATES = [
            (pd.Timestamp("2025-01-14"), 10.0),
            (pd.Timestamp("2024-06-11"), 9.0),
            (pd.Timestamp("2024-03-12"), 8.08),
            (pd.Timestamp("2024-01-09"), 8.02),  # Clove 출시
        ]
        for cutoff, patch in sorted(PATCH_DATES, reverse=True):
            if date >= cutoff:
                return patch
        return 6.0  # 기본값 (아주 오래된 데이터)
    except:
        return 0.0
```

---

### I005: 신규 요원 희소 데이터

**원인:** Clove(EP8.02), Tejo(EP10.x), Waylay(EP10.x)는 최신 요원으로 학습 데이터 부족.

**현황:**
| 요원 | 출시 패치 | 예상 학습 샘플 | 위험도 |
|------|--------|------------|------|
| Clove | EP8.02 (2024.01) | 보통 | 낮음 |
| Tejo | EP10.x (2025) | 매우 적음 | 높음 |
| Waylay | EP10.x (2025) | 매우 적음 | 높음 |

**처리 전략:**
```python
RARE_AGENTS = {"Tejo", "Waylay"}

def check_agent_frequency(df: pd.DataFrame, min_appearances: int = 50) -> dict:
    """요원별 등장 횟수 확인"""
    all_agents = []
    for col in ["team_a_agents", "team_b_agents"]:
        if col in df.columns:
            df[col].dropna().apply(
                lambda x: all_agents.extend(a.strip() for a in str(x).split(","))
            )
    
    from collections import Counter
    counts = Counter(all_agents)
    rare = {agent: count for agent, count in counts.items() if count < min_appearances}
    
    if rare:
        print(f"[I005] 희소 요원 ({min_appearances}회 미만): {rare}")
    
    return dict(counts)
```

---

### I009: Lotus 이름 충돌

**원인:** `Lotus`가 맵 이름이기도 하고, 과거 일부 파서에서 파싱 오류 가능성.

**처리:**
```python
# team_a_agents 컬럼에서 "Lotus" 발견 시 → 맵명 혼입 오류
def check_lotus_collision(df: pd.DataFrame) -> int:
    """요원 컬럼에 맵명 혼입 여부 확인"""
    errors = 0
    for col in ["team_a_agents", "team_b_agents"]:
        if col not in df.columns:
            continue
        lotus_in_agents = df[col].apply(
            lambda x: "Lotus" in str(x).split(",")
        ).sum()
        if lotus_in_agents > 0:
            print(f"[I009] {col}에 'Lotus' 발견: {lotus_in_agents}행 → 맵명 혼입 의심")
            errors += lotus_in_agents
    return errors
```

---

## 3. 이슈 모니터링 체크리스트

데이터 수집 후 반드시 실행:

```python
def run_issue_checks(df: pd.DataFrame) -> None:
    """알려진 이슈 사전 점검"""
    print("[점검] I001 KAY/O 정규화...")
    # validate_agent_names()에서 처리됨
    
    print("[점검] I002 비활성 맵...")
    retired = df[df["map"].isin(RETIRED_MAPS)] if "map" in df.columns else pd.DataFrame()
    if len(retired) > 0:
        print(f"  ⚠️ 비활성 맵 {len(retired)}행 발견")
    
    print("[점검] I005 희소 요원...")
    agent_counts = check_agent_frequency(df, min_appearances=50)
    
    print("[점검] I009 Lotus 충돌...")
    check_lotus_collision(df)
    
    print("[점검] I010 중복 경기...")
    if "match_id" in df.columns:
        dup_rate = df.duplicated(subset=["match_id"]).sum() / len(df)
        if dup_rate > 0.05:
            print(f"  ⚠️ 중복 비율 {dup_rate:.1%} (5% 초과)")
```
