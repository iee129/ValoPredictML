"""발로란트 요원/맵/팀 정규화 및 분류.

데이터셋에 나타나는 모든 표기 변형을 흡수해 일관된 키로 변환한다.
모든 알려진 이름은 소문자 + 공백 strip 후 비교.
"""
from __future__ import annotations

# ───────── 요원 → 5 역할 (역할 one-hot 카테고리) ─────────
# 듀얼리스트는 1선(first_duelist) / 2선(second_duelist) 으로 세분화.
AGENT_ROLES: dict[str, str] = {
    # first_duelist (1선): 먼저 들어가 첫 킬 따내는 공격적 듀얼
    "jett": "first_duelist",
    "raze": "first_duelist",
    "neon": "first_duelist",
    "waylay": "first_duelist",
    # second_duelist (2선): 1선 뒤에서 받쳐주는 보조 듀얼
    "phoenix": "second_duelist",
    "reyna": "second_duelist",
    "yoru": "second_duelist",
    "iso": "second_duelist",
    # initiator (척후)
    "sova": "initiator",
    "breach": "initiator",
    "skye": "initiator",
    "kay/o": "initiator",
    "fade": "initiator",
    "gekko": "initiator",
    "tejo": "initiator",
    # controller (전략)
    "omen": "controller",
    "brimstone": "controller",
    "viper": "controller",
    "astra": "controller",
    "harbor": "controller",
    "clove": "controller",
    # sentinel (감시)
    "sage": "sentinel",
    "killjoy": "sentinel",
    "cypher": "sentinel",
    "chamber": "sentinel",
    "deadlock": "sentinel",
    "vyse": "sentinel",
}

ROLES = ("first_duelist", "second_duelist", "initiator", "controller", "sentinel")

# 포지션 (슬롯 정렬/라벨용). 역할과 같은 5 카테고리지만 이름만 다르다.
#   first_duelist  → duelist1
#   second_duelist → duelist2
#   나머지는 역할명 그대로
_ROLE_TO_POSITION = {
    "first_duelist": "duelist1",
    "second_duelist": "duelist2",
    "initiator": "initiator",
    "controller": "controller",
    "sentinel": "sentinel",
}
POSITIONS = ("duelist1", "duelist2", "initiator", "controller", "sentinel")

# 데이터셋에서 발견된 표기 → 표준 표기.
# 빈 dict로 시작; 첫 실행 시 unmatched가 stderr에 찍히면 여기에 추가.
_AGENT_ALIASES: dict[str, str] = {
    "kayo": "kay/o",
    "kay_o": "kay/o",
    "kay-o": "kay/o",
    "brim": "brimstone",
}


# ───────── 맵 ─────────
MAP_LIST: list[str] = [
    "bind",
    "haven",
    "split",
    "ascent",
    "icebox",
    "breeze",
    "fracture",
    "pearl",
    "lotus",
    "sunset",
    "abyss",
    "corrode",
]
MAP_TO_IDX: dict[str, int] = {m: i for i, m in enumerate(MAP_LIST)}

# 맵 별 글로벌 공격측 승률 placeholder.
# 추후 vct_dataset/agents/maps_stats.csv 누적 평균으로 override 가능.
ATTACKER_ADVANTAGE: dict[str, float] = {m: 0.5 for m in MAP_LIST}

_MAP_ALIASES: dict[str, str] = {}


# ───────── 팀 alias ─────────
# 팀명은 시즌마다 미세하게 다른 표기로 등장. 발견 시 여기에 추가.
_TEAM_ALIASES: dict[str, str] = {}


# ───────── 정규화 함수 ─────────
def _basic_norm(s: str) -> str:
    return s.strip().lower()


def normalize_agent(name: str) -> str | None:
    """요원명 → 표준 키. 모르는 이름이면 None."""
    if name is None:
        return None
    key = _basic_norm(str(name))
    if not key:
        return None
    key = _AGENT_ALIASES.get(key, key)
    if key in AGENT_ROLES:
        return key
    return None


def normalize_map(name: str) -> str | None:
    """맵명 → 표준 키 (소문자). 모르는 맵이면 None."""
    if name is None:
        return None
    key = _basic_norm(str(name))
    if not key:
        return None
    key = _MAP_ALIASES.get(key, key)
    if key in MAP_TO_IDX:
        return key
    return None


def normalize_team(name: str) -> str | None:
    """팀명 → 표준 표기. 모르는 alias도 일단 그대로 반환 (소문자 정규화만)."""
    if name is None:
        return None
    key = _basic_norm(str(name))
    if not key:
        return None
    key = _TEAM_ALIASES.get(key, key)
    return key


def normalize_player(name: str) -> str | None:
    """선수명은 대소문자 외엔 표준화하지 않음. 빈/누락이면 None."""
    if name is None:
        return None
    s = str(name).strip()
    return s if s else None


def agent_role(agent_name: str) -> str | None:
    """요원 이름 → 5 역할 (first_duelist/second_duelist/initiator/controller/sentinel)."""
    key = normalize_agent(agent_name)
    if key is None:
        return None
    return AGENT_ROLES[key]


def agent_position(agent_name: str) -> str | None:
    """요원 이름 → 5 포지션 (duelist1/duelist2/initiator/controller/sentinel)."""
    role = agent_role(agent_name)
    if role is None:
        return None
    return _ROLE_TO_POSITION[role]


def roster_composition(agents: list[str]) -> dict[str, int]:
    """5명 요원 리스트 → 롤별 count. 미인식 요원은 'unknown' 키로 집계."""
    out = {r: 0 for r in ROLES}
    out["unknown"] = 0
    for a in agents:
        r = agent_role(a)
        if r is None:
            out["unknown"] += 1
        else:
            out[r] += 1
    return out


def map_idx(name: str) -> int:
    """맵 이름 → 정수 인덱스. 미인식이면 -1."""
    key = normalize_map(name)
    if key is None:
        return -1
    return MAP_TO_IDX[key]


def attacker_advantage(name: str) -> float:
    """맵별 공격측 승률 placeholder. 미인식이면 0.5."""
    key = normalize_map(name)
    if key is None:
        return 0.5
    return ATTACKER_ADVANTAGE.get(key, 0.5)
