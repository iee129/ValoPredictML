from __future__ import annotations

import re

from ml.agent_roles import AGENT_ROLE_MAP, MAP_ORDER, MAP_TO_INDEX

__all__ = [
    "AGENT_ROLE_MAP", "MAP_ORDER", "MAP_TO_INDEX",
    "AGENTS_SORTED", "ROLES",
    "_agent_col_key", "_AGENT_KEY_TO_ROLE",
    "agent_feature_columns", "role_feature_columns", "map_feature_columns",
    "normalize_agent", "normalize_map",
]

ROLES: list[str] = ["duelist", "initiator", "controller", "sentinel"]

_AGENT_ALIASES: dict[str, str] = {
    "kayo": "KAY/O",
    "kay/o": "KAY/O",
    "kay-o": "KAY/O",
    "iso": "ISO",
    "waylay": "Waylay",
    "tejo": "Tejo",
    "clove": "Clove",
    "vyse": "Vyse",
    "veto": "Veto",
    "deadlock": "Deadlock",
    "gekko": "Gekko",
    "fade": "Fade",
    "harbor": "Harbor",
    "neon": "Neon",
    "yoru": "Yoru",
    "miks": "Miks",
}


def normalize_agent(raw: str) -> str | None:
    """Return canonical agent name (as in AGENT_ROLE_MAP), or None if unknown."""
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if s in AGENT_ROLE_MAP:
        return s
    lower = s.lower()
    if lower in _AGENT_ALIASES:
        return _AGENT_ALIASES[lower]
    titled = s.title()
    if titled in AGENT_ROLE_MAP:
        return titled
    return None


def normalize_map(raw: str) -> str | None:
    """Return canonical map name (as in MAP_ORDER), or None if unknown."""
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if s in MAP_TO_INDEX:
        return s
    titled = s.title()
    if titled in MAP_TO_INDEX:
        return titled
    return None


def _agent_col_key(agent: str) -> str:
    """Convert canonical agent name to feature-column key (lowercase, alphanumeric).

    "KAY/O" → "kayo", "ISO" → "iso", "Jett" → "jett"
    """
    return re.sub(r"[^a-z0-9]", "", agent.lower())


AGENTS_SORTED: list[str] = sorted({_agent_col_key(a) for a in AGENT_ROLE_MAP})

_AGENT_KEY_TO_ROLE: dict[str, str] = {
    _agent_col_key(agent): role.lower()
    for agent, role in AGENT_ROLE_MAP.items()
}


def agent_feature_columns() -> list[str]:
    """Returns a_<agent>, b_<agent>, diff_<agent> for every agent — 87 cols (29 × 3)."""
    cols: list[str] = []
    for a in AGENTS_SORTED:
        cols += [f"a_{a}", f"b_{a}", f"diff_{a}"]
    return cols


def role_feature_columns() -> list[str]:
    """Returns a_<role>, b_<role>, diff_<role> — 12 cols (4 × 3)."""
    cols: list[str] = []
    for r in ROLES:
        cols += [f"a_{r}", f"b_{r}", f"diff_{r}"]
    return cols


def map_feature_columns() -> list[str]:
    """Returns map_<name> binary columns — 13 cols."""
    return [f"map_{m.lower()}" for m in MAP_ORDER]
