# 02. 요원 역할군 매핑 테이블

## 1. 전체 요원 목록 (2025년 기준, 27종)

| 요원 | 역할군 (EN) | 역할군 (KO) | 출시 에피소드 | 비고 |
|------|-----------|-----------|------------|------|
| Jett | Duelist | 듀얼리스트 | EP 1 | 초기 출시 |
| Reyna | Duelist | 듀얼리스트 | EP 1 | 초기 출시 |
| Phoenix | Duelist | 듀얼리스트 | EP 1 | 초기 출시 |
| Raze | Duelist | 듀얼리스트 | EP 1 | 초기 출시 |
| Yoru | Duelist | 듀얼리스트 | EP 2 Act 1 | |
| Neon | Duelist | 듀얼리스트 | EP 4 Act 1 | |
| ISO | Duelist | 듀얼리스트 | EP 7 Act 3 | |
| Waylay | Duelist | 듀얼리스트 | EP 10 Act 2 | 2025년 신규 |
| Sova | Initiator | 이니시에이터 | EP 1 | 초기 출시 |
| Breach | Initiator | 이니시에이터 | EP 1 | 초기 출시 |
| Skye | Initiator | 이니시에이터 | EP 1 Act 3 | |
| KAY/O | Initiator | 이니시에이터 | EP 3 Act 1 | |
| Fade | Initiator | 이니시에이터 | EP 4 Act 3 | |
| Gekko | Initiator | 이니시에이터 | EP 6 Act 2 | |
| Tejo | Initiator | 이니시에이터 | EP 10 Act 1 | 2025년 신규 |
| Viper | Controller | 컨트롤러 | EP 1 | 초기 출시 |
| Omen | Controller | 컨트롤러 | EP 1 | 초기 출시 |
| Brimstone | Controller | 컨트롤러 | EP 1 | 초기 출시 |
| Astra | Controller | 컨트롤러 | EP 2 Act 2 | |
| Harbor | Controller | 컨트롤러 | EP 5 Act 3 | |
| Clove | Controller | 컨트롤러 | EP 8 Act 2 | 2024년 신규 |
| Killjoy | Sentinel | 센티넬 | EP 1 Act 2 | |
| Cypher | Sentinel | 센티넬 | EP 1 | 초기 출시 |
| Sage | Sentinel | 센티넬 | EP 1 | 초기 출시 |
| Chamber | Sentinel | 센티넬 | EP 3 Act 3 | |
| Deadlock | Sentinel | 센티넬 | EP 7 Act 1 | |
| Vyse | Sentinel | 센티넬 | EP 9 Act 2 | |

---

## 2. Python 코드 — 전체 매핑

```python
# 최신 요원 역할군 매핑 (2025년 기준)
AGENT_ROLE_MAP: dict[str, str] = {
    # === Duelist (8종) ===
    "Jett":    "Duelist",
    "Reyna":   "Duelist",
    "Phoenix": "Duelist",
    "Raze":    "Duelist",
    "Yoru":    "Duelist",
    "Neon":    "Duelist",
    "ISO":     "Duelist",
    "Waylay":  "Duelist",
    
    # === Initiator (7종) ===
    "Sova":   "Initiator",
    "Breach": "Initiator",
    "Skye":   "Initiator",
    "KAY/O":  "Initiator",
    "Fade":   "Initiator",
    "Gekko":  "Initiator",
    "Tejo":   "Initiator",
    
    # === Controller (6종) ===
    "Viper":     "Controller",
    "Omen":      "Controller",
    "Brimstone": "Controller",
    "Astra":     "Controller",
    "Harbor":    "Controller",
    "Clove":     "Controller",
    
    # === Sentinel (6종) ===
    "Killjoy":  "Sentinel",
    "Cypher":   "Sentinel",
    "Sage":     "Sentinel",
    "Chamber":  "Sentinel",
    "Deadlock": "Sentinel",
    "Vyse":     "Sentinel",
}

# 역할군 목록
ROLE_NAMES = ["Duelist", "Initiator", "Controller", "Sentinel"]

# 역할군별 요원 목록 (역 인덱스)
ROLE_TO_AGENTS: dict[str, list[str]] = {}
for agent, role in AGENT_ROLE_MAP.items():
    ROLE_TO_AGENTS.setdefault(role, []).append(agent)
```

---

## 3. 이름 변형 표준화 테이블

데이터셋마다 요원 이름 표기가 다를 수 있음:

```python
AGENT_ALIASES: dict[str, str] = {
    # KAY/O 변형
    "kayo":    "KAY/O",
    "kay/o":   "KAY/O",
    "kay-o":   "KAY/O",
    "kay_o":   "KAY/O",
    "k/o":     "KAY/O",
    
    # ISO 변형
    "iso":     "ISO",
    "Iso":     "ISO",
    
    # 공백/대소문자 변형
    "neon ":   "Neon",
    "jett ":   "Jett",
    
    # 기타
    "breach":  "Breach",
    "viper":   "Viper",
    "omen":    "Omen",
    "sage":    "Sage",
}

def normalize_agent_name(raw: str) -> str:
    """요원 이름 표준화"""
    stripped = raw.strip()
    # 이미 알려진 이름인지 확인
    if stripped in AGENT_ROLE_MAP:
        return stripped
    # 소문자 변형 확인
    lower = stripped.lower()
    if lower in AGENT_ALIASES:
        return AGENT_ALIASES[lower]
    # Title case 시도
    titled = stripped.title()
    if titled in AGENT_ROLE_MAP:
        return titled
    
    print(f"[WARN] 알 수 없는 요원: '{raw}'")
    return raw
```

---

## 4. 역할군 카운트 함수

```python
def count_agent_roles(agents: list[str]) -> dict[str, int]:
    """
    요원 이름 목록 → 역할군별 카운트
    
    Args:
        agents: ['Jett', 'Sova', 'Viper', 'Omen', 'Killjoy']
    
    Returns:
        {'Duelist': 1, 'Initiator': 1, 'Controller': 2, 'Sentinel': 1}
    """
    counts = {role: 0 for role in ROLE_NAMES}
    unknown = []
    
    for raw_agent in agents:
        agent = normalize_agent_name(raw_agent)
        role = AGENT_ROLE_MAP.get(agent)
        if role:
            counts[role] += 1
        else:
            unknown.append(agent)
    
    if unknown:
        print(f"[WARN] 역할군 미분류 요원: {unknown}")
    
    return counts


# 사용 예시
agents_team_a = ["Jett", "Sova", "Viper", "Omen", "Killjoy"]
counts = count_agent_roles(agents_team_a)
# → {'Duelist': 1, 'Initiator': 1, 'Controller': 2, 'Sentinel': 1}
```

---

## 5. 에피소드별 요원 가용성

일부 데이터셋은 오래된 에피소드의 경기를 포함.  
해당 시점에 출시되지 않은 요원이 등장하면 데이터 오류로 처리:

```python
# 요원 출시 에피소드 (주요 요원만)
AGENT_RELEASE = {
    "ISO":      "7.0",   # EP 7
    "Deadlock": "7.0",
    "Clove":    "8.0",   # EP 8 Act 2
    "Vyse":     "9.0",
    "Tejo":     "10.0",
    "Waylay":   "10.2",
}

def validate_agents_for_patch(agents: list[str], patch: str) -> list[str]:
    """패치 버전에서 사용 불가능한 요원 필터링"""
    patch_float = float(patch.replace("-", "").split(".")[:2][-1]) if patch else 99.0
    valid = []
    for agent in agents:
        release = AGENT_RELEASE.get(agent, "1.0")
        if float(release) <= patch_float:
            valid.append(agent)
        else:
            print(f"[WARN] {agent}는 패치 {patch}에서 미출시")
    return valid
```
