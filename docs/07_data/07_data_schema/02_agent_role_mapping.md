# 02. 요원 역할군 매핑 (29종)

마지막 업데이트: 2026-05-04

---

## 1. 전체 요원 목록 (2025년 기준)

| 요원 | 역할군 | 역할군 (한국어) | 출시 |
|------|--------|--------------|------|
| Jett | Duelist | 타격대 | EP 1 |
| Reyna | Duelist | 타격대 | EP 1 |
| Phoenix | Duelist | 타격대 | EP 1 |
| Raze | Duelist | 타격대 | EP 1 |
| Yoru | Duelist | 타격대 | EP 2 Act 1 |
| Neon | Duelist | 타격대 | EP 4 Act 1 |
| ISO | Duelist | 타격대 | EP 7 Act 3 |
| Waylay | Duelist | 타격대 | EP 10 Act 2 |
| Sova | Initiator | 척후대 | EP 1 |
| Breach | Initiator | 척후대 | EP 1 |
| Skye | Initiator | 척후대 | EP 1 Act 3 |
| KAY/O | Initiator | 척후대 | EP 3 Act 1 |
| Fade | Initiator | 척후대 | EP 4 Act 3 |
| Gekko | Initiator | 척후대 | EP 6 Act 2 |
| Tejo | Initiator | 척후대 | EP 10 Act 1 |
| Viper | Controller | 전략가 | EP 1 |
| Omen | Controller | 전략가 | EP 1 |
| Brimstone | Controller | 전략가 | EP 1 |
| Astra | Controller | 전략가 | EP 2 Act 2 |
| Harbor | Controller | 전략가 | EP 5 Act 3 |
| Clove | Controller | 전략가 | EP 8 Act 2 |
| Killjoy | Sentinel | 감시자 | EP 1 Act 2 |
| Cypher | Sentinel | 감시자 | EP 1 |
| Sage | Sentinel | 감시자 | EP 1 |
| Chamber | Sentinel | 감시자 | EP 3 Act 3 |
| Deadlock | Sentinel | 감시자 | EP 7 Act 1 |
| Vyse | Sentinel | 감시자 | EP 9 Act 2 |
| Veto | Sentinel | 감시자 | EP 10 Act 3 |
| Miks | Controller | 전략가 | EP 10 Act 3 |

역할군 분류: Duelist 8종 / Initiator 7종 / Controller 7종 / Sentinel 7종

---

## 2. AGENT_ROLE_MAP (Python)

```python
AGENT_ROLE_MAP: dict[str, str] = {
    # Duelist (8종)
    "Jett": "Duelist", "Reyna": "Duelist", "Phoenix": "Duelist",
    "Raze": "Duelist", "Yoru": "Duelist", "Neon": "Duelist",
    "ISO": "Duelist", "Waylay": "Duelist",
    # Initiator (7종)
    "Sova": "Initiator", "Breach": "Initiator", "Skye": "Initiator",
    "KAY/O": "Initiator", "Fade": "Initiator", "Gekko": "Initiator",
    "Tejo": "Initiator",
    # Controller (7종)
    "Viper": "Controller", "Omen": "Controller", "Brimstone": "Controller",
    "Astra": "Controller", "Harbor": "Controller", "Clove": "Controller",
    "Miks": "Controller",
    # Sentinel (7종)
    "Killjoy": "Sentinel", "Cypher": "Sentinel", "Sage": "Sentinel",
    "Chamber": "Sentinel", "Deadlock": "Sentinel", "Vyse": "Sentinel",
    "Veto": "Sentinel",
}
```

---

## 3. 이름 변형 표준화 (AGENT_ALIASES)

```python
AGENT_ALIASES: dict[str, str] = {
    "kayo": "KAY/O", "kay/o": "KAY/O", "kay-o": "KAY/O", "kay_o": "KAY/O",
    "iso": "ISO",
}

def normalize_agent(raw: str) -> str | None:
    """요원 이름 표준화. 없으면 None → 품질 검사 탈락."""
    s = raw.strip()
    if s in AGENT_ROLE_MAP:
        return s
    lower = s.lower()
    if lower in AGENT_ALIASES:
        return AGENT_ALIASES[lower]
    titled = s.title()
    if titled in AGENT_ROLE_MAP:
        return titled
    return None
```

`normalize_agent()` 처리 순서:
1. `AGENT_ROLE_MAP`에 그대로 있으면 반환
2. 소문자 → `AGENT_ALIASES` 조회 (`"kayo"` → `"KAY/O"`)
3. `.title()` 시도 후 재확인
4. 없으면 `None` → 품질 검사 탈락

---

## 4. 팀명 정규화 (TEAM_NAME_ALIASES)

소스마다 팀명 표기가 달라 dedup_key 생성 전 반드시 정규화.

```python
TEAM_NAME_ALIASES: dict[str, str] = {
    "t1 korea":       "T1",
    "team one korea": "T1",
    "natus vincere":  "NAVI",
    "navi":           "NAVI",
    "fnatic":         "FNC",
    "cloud9":         "C9",
    # 파싱 실행 중 불일치 발견 시 추가
}

def normalize_team(raw: str) -> str:
    return TEAM_NAME_ALIASES.get(raw.strip().lower(), raw.strip())
```

파서 A~D 모두에서 `team_a`, `team_b` 값 확정 직후 호출.
