from __future__ import annotations  # 파이썬이 좀 더 새로운 방식으로 '자료형 이름표'를 읽을 수 있게 해주는 마법 주문이에요

AGENT_ROLE_MAP: dict[str, str] = {  # 발로란트 요원 이름을 보면 그 요원이 어떤 역할군인지 바로 찾을 수 있는 표예요 — 마치 반 친구 이름표에 역할이 적혀 있는 것처럼
    # Duelist (8종)
    "Jett": "Duelist", "Reyna": "Duelist", "Phoenix": "Duelist",  # 제트·레이나·피닉스는 타격대(Duelist) — 적을 직접 공격하는 역할이에요
    "Raze": "Duelist", "Yoru": "Duelist", "Neon": "Duelist",  # 레이즈·요루·네온도 타격대(Duelist) — 빠르게 싸우는 공격수들이에요
    "ISO": "Duelist", "Waylay": "Duelist",  # ISO·웨이레이도 타격대(Duelist) — 적과 1대1로 싸우는 것을 잘해요
    # Initiator (7종)
    "Sova": "Initiator", "Breach": "Initiator", "Skye": "Initiator",  # 소바·브리치·스카이는 척후대(Initiator) — 팀이 들어가기 전에 먼저 정보를 모아줘요
    "KAY/O": "Initiator", "Fade": "Initiator", "Gekko": "Initiator",  # KAY/O·페이드·게코도 척후대(Initiator) — 적을 약하게 만들어 팀을 도와줘요
    "Tejo": "Initiator",  # 테호도 척후대(Initiator) — 2025년에 새로 나온 척후대 요원이에요
    # Controller (6종)
    "Viper": "Controller", "Omen": "Controller", "Brimstone": "Controller",  # 바이퍼·오멘·브림스톤은 전략가(Controller) — 연기나 불꽃으로 지역을 막아 팀을 돕는 역할이에요
    "Astra": "Controller", "Harbor": "Controller", "Clove": "Controller",  # 아스트라·하버·클로브도 전략가(Controller) — 싸움터를 우리 팀에게 유리하게 만들어줘요
    # Sentinel (7종 — 2025-10 신규 Veto 추가)
    "Killjoy": "Sentinel", "Cypher": "Sentinel", "Sage": "Sentinel",  # 킬조이·사이퍼·세이지는 감시자(Sentinel) — 아군을 보호하고 적의 움직임을 감시하는 역할이에요
    "Chamber": "Sentinel", "Deadlock": "Sentinel", "Vyse": "Sentinel",  # 체임버·데드락·바이스도 감시자(Sentinel) — 팀이 안전하게 싸울 수 있도록 지켜줘요
    "Veto": "Sentinel",  # 베토는 7번째 감시자(Sentinel) — 2025년 10월에 새로 나온 요원이에요 (mutation DNA 능력)
    # Controller에 Miks 추가 (위 Controller 줄에 추가됨)
    "Miks": "Controller",  # 믹스는 7번째 전략가(Controller) — 2026년 3월에 새로 나온 요원이에요 (음파 능력)
}

MAP_ORDER: list[str] = [  # 발로란트에 있는 공식 맵(전투 장소) 목록이에요 — 이 순서가 나중에 맵마다 번호를 붙일 때 쓰여요
    "Ascent", "Bind", "Haven", "Split", "Icebox", "Breeze",  # 게임 출시 초기에 나온 맵 6개예요
    "Fracture", "Pearl", "Lotus", "Sunset", "Abyss", "Drift",  # 나중에 추가된 맵 6개예요 (Drift는 TDM 모드용)
    "Corrode",  # 코로드는 2025년 6월에 새로 나온 spike 모드 맵이에요 (12번째 정식 맵, France 테마)
]
MAP_TO_INDEX: dict[str, int] = {m: i for i, m in enumerate(MAP_ORDER)}  # 맵 이름을 보면 그 번호(0, 1, 2...)를 바로 찾을 수 있는 표예요 — 컴퓨터가 맵 이름 대신 숫자로 처리할 수 있게 해줘요

# 맵별 공격 측 유리 정도 (양수=공격 유리, 음수=수비 유리, 0=균형)
ATK_ADV_MAP: dict[str, float] = {  # 각 맵에서 공격하는 팀이 얼마나 유리한지 수치로 나타낸 표예요 — 0이면 공평하고, +이면 공격이 유리, -이면 수비가 유리해요
    "Ascent":   0.0,  # 어센트: 공격과 수비가 딱 절반씩 공평해요
    "Bind":    -0.1,  # 바인드: 텔레포터 구조 때문에 수비 팀이 살짝 유리해요 (수비가 0.1만큼 더 유리)
    "Haven":    0.1,  # 헤이븐: 폭탄 설치 장소가 3개라 공격 팀이 살짝 유리해요 (공격이 0.1만큼 더 유리)
    "Split":   -0.05,  # 스플릿: 좁은 통로 구조라 수비 팀이 아주 조금 유리해요
    "Icebox":   0.0,  # 아이스박스: 공격과 수비가 공평해요
    "Breeze":   0.05,  # 브리즈: 넓은 공간 덕분에 공격 팀이 아주 조금 유리해요
    "Fracture": 0.05,  # 프랙처: 공격 팀이 양쪽에서 동시에 들어올 수 있어서 아주 조금 유리해요
    "Pearl":    0.0,  # 펄: 공격과 수비가 공평해요
    "Lotus":    0.05,  # 로터스: 폭탄 설치 장소가 3개라 공격 팀이 아주 조금 유리해요
    "Sunset":   0.0,  # 선셋: 공격과 수비가 공평해요
    "Abyss":    0.0,  # 어비스: 공격과 수비가 공평해요
    "Drift":    0.0,  # 드리프트: 공격과 수비가 공평해요
    "Corrode":  0.014,  # 코로드: VCT 2025 Champions 어택 51.4%로 살짝 어택이 유리해요 (Liquipedia 검증 2026-05-09)
}

TEAM_NAME_ALIASES: dict[str, str] = {  # 같은 팀인데 여러 가지 이름으로 불리는 경우, 하나의 공식 이름으로 통일하는 표예요 — 마치 친구의 별명을 본명으로 바꿔 주는 것처럼
    "t1 korea":       "T1",  # "T1 Korea"라고 불려도 공식 팀 이름은 "T1"이에요
    "team one korea": "T1",  # "Team One Korea"라고 불려도 공식 팀 이름은 "T1"이에요
    "natus vincere":  "NAVI",  # 풀 이름 "Natus Vincere"를 짧게 "NAVI"로 통일해요
    "navi":           "NAVI",  # 소문자로 써도 공식 약칭 "NAVI"로 통일해요
    "fnatic":         "FNC",  # "fnatic"을 약칭 "FNC"로 통일해요
    "cloud9":         "C9",  # "cloud9"을 약칭 "C9"으로 통일해요
}

EVENT_NAME_ALIASES: dict[str, str] = {  # 같은 대회인데 여러 이름으로 불리는 경우, 하나의 공식 이름으로 통일하는 표예요
    "vct 2024 americas league stage 1": "VCT_2024_Americas_S1",  # 긴 대회 이름을 짧은 코드로 통일해요
    "vct americas stage 1":              "VCT_2024_Americas_S1",  # 줄인 이름도 같은 공식 코드로 통일해요
}

PLAYER_NAME_ALIASES: dict[str, str] = {}  # 선수 이름 별명 모음인데 지금은 비어 있어요 — 나중에 필요하면 여기에 추가할 거예요

# 소문자 소스 표기 → 정규 요원명
_AGENT_ALIASES: dict[str, str] = {  # 요원 이름이 소문자로 오거나 철자가 조금 다를 때, 올바른 공식 이름으로 바꿔 주는 표예요 — 마치 맞춤법 교정 사전처럼
    "kayo":     "KAY/O",  # 슬래시(/) 없이 쓴 경우도 공식 이름 "KAY/O"로 바꿔줘요
    "kay/o":    "KAY/O",  # 소문자로 써도 대문자 공식 이름 "KAY/O"로 바꿔줘요
    "kayo/":    "KAY/O",  # 슬래시 위치가 틀려도 공식 이름으로 바꿔줘요
    "kay-o":    "KAY/O",  # 하이픈(-)으로 쓴 경우도 슬래시 있는 공식 이름으로 바꿔줘요
    "iso":      "ISO",  # 소문자 "iso"를 대문자 공식 이름 "ISO"로 바꿔줘요
    "waylay":   "Waylay",  # 소문자를 공식 표기 "Waylay"로 바꿔줘요 (최근에 추가된 요원이에요)
    "tejo":     "Tejo",  # 소문자를 공식 표기 "Tejo"로 바꿔줘요 (2025년 새로 나온 척후대 요원)
    "clove":    "Clove",  # 소문자를 공식 표기 "Clove"로 바꿔줘요 (전략가 역할)
    "vyse":     "Vyse",  # 소문자를 공식 표기 "Vyse"로 바꿔줘요 (감시자 역할)
    "deadlock": "Deadlock",  # 소문자를 공식 표기 "Deadlock"으로 바꿔줘요 (감시자 역할)
    "gekko":    "Gekko",  # 소문자를 공식 표기 "Gekko"로 바꿔줘요 (척후대 역할)
    "fade":     "Fade",  # 소문자를 공식 표기 "Fade"로 바꿔줘요 (척후대 역할)
    "harbor":   "Harbor",  # 소문자를 공식 표기 "Harbor"로 바꿔줘요 (전략가 역할)
    "neon":     "Neon",  # 소문자를 공식 표기 "Neon"으로 바꿔줘요 (타격대 역할)
    "yoru":     "Yoru",  # 소문자를 공식 표기 "Yoru"로 바꿔줘요 (타격대 역할)
    "miks":     "Miks",  # 소문자를 공식 표기 "Miks"로 바꿔줘요 (2026-03 신규 전략가/Controller)
    "veto":     "Veto",  # 소문자를 공식 표기 "Veto"로 바꿔줘요 (2025-10 신규 감시자/Sentinel)
    "corrode":  "Corrode",  # 맵 alias도 추가하지만 normalize_map은 따로 처리됨 (이 항목은 통일성을 위해 표기)
}


def normalize_agent(raw: str) -> str | None:  # 다양하게 쓰인 요원 이름을 공식 이름으로 바꿔 주는 함수예요 — 바꿀 수 없으면 None(아무것도 없음)을 돌려줘요
    if not raw or not isinstance(raw, str):  # 입력이 비어 있거나 글자가 아니면 바꿀 수 없으니 바로 끝내요
        return None  # 올바른 입력이 아니라서 아무것도 돌려주지 않아요
    s = raw.strip()  # 앞뒤에 붙어 있는 빈칸을 지워요 (예: "  Jett  " → "Jett")
    if s in AGENT_ROLE_MAP:  # 이미 공식 이름이면 그대로 돌려줘요 — 교정이 필요 없어요
        return s  # 공식 이름 그대로 돌려줘요
    lower = s.lower()  # 대소문자 상관없이 비교하려고 모두 소문자로 바꿔요 (예: "JETT" → "jett")
    if lower in _AGENT_ALIASES:  # 소문자로 바꾼 이름이 별명 표에 있으면 공식 이름으로 교체해요
        return _AGENT_ALIASES[lower]  # 별명 표에서 공식 요원 이름을 꺼내 돌려줘요
    titled = s.title()  # 각 단어의 첫 글자만 대문자로 바꿔요 (예: "killjoy" → "Killjoy")
    if titled in AGENT_ROLE_MAP:  # 첫 글자 대문자로 바꿨을 때 공식 이름과 같으면 돌려줘요
        return titled  # 첫 글자 대문자로 바꾼 공식 요원 이름을 돌려줘요
    return None  # 어떻게 해도 공식 이름을 찾지 못하면 아무것도 없다는 뜻의 None을 돌려줘요


def get_role(agent: str) -> str | None:  # 요원 이름을 주면 그 요원의 역할군(타격대·척후대 등)을 알려주는 함수예요
    norm = normalize_agent(agent)  # 먼저 요원 이름을 공식 표기로 바꿔요
    if norm is None:  # 공식 이름을 찾지 못하면 역할군도 알 수 없어요
        return None  # 역할군을 알 수 없다는 뜻의 None을 돌려줘요
    return AGENT_ROLE_MAP.get(norm)  # 공식 요원 이름으로 역할군 표를 찾아 역할군을 돌려줘요


def normalize_map(raw: str) -> str | None:  # 다양하게 쓰인 맵 이름을 공식 맵 이름으로 바꿔 주는 함수예요 — 바꿀 수 없으면 None을 돌려줘요
    if not raw or not isinstance(raw, str):  # 입력이 비어 있거나 글자가 아니면 바꿀 수 없으니 바로 끝내요
        return None  # 올바른 입력이 아니라서 아무것도 돌려주지 않아요
    s = raw.strip()  # 앞뒤 빈칸을 지워요
    if s in MAP_TO_INDEX:  # 이미 공식 맵 이름이면 그대로 돌려줘요
        return s  # 공식 맵 이름 그대로 돌려줘요
    titled = s.title()  # 첫 글자만 대문자로 바꿔요 (예: "ascent" → "Ascent")
    if titled in MAP_TO_INDEX:  # 첫 글자 대문자로 바꾼 결과가 공식 이름과 같으면 돌려줘요
        return titled  # 첫 글자 대문자 공식 맵 이름을 돌려줘요
    return None  # 알 수 없는 맵 이름이면 아무것도 없다는 뜻의 None을 돌려줘요


def map_encoded(map_name: str) -> int:  # 맵 이름을 컴퓨터가 이해하기 쉬운 숫자(번호)로 바꿔 주는 함수예요
    norm = normalize_map(map_name)  # 먼저 맵 이름을 공식 표기로 바꿔요
    if norm is None:  # 공식 이름을 찾지 못하면 '모르는 맵'을 나타내는 특별한 숫자를 돌려줘요
        return -1  # -1은 '이 맵은 모른다'는 신호예요 — 목록에 없는 맵이에요
    return MAP_TO_INDEX[norm]  # 공식 맵 이름으로 번호 표를 찾아 그 번호를 돌려줘요


def normalize_team(raw: str) -> str:  # 여러 가지로 불리는 팀 이름을 공식 팀 이름으로 통일해 주는 함수예요
    if not raw or not isinstance(raw, str):  # 입력이 비어 있거나 글자가 아니면 그냥 글자로 바꿔서 돌려줘요
        return str(raw).strip()  # 글자로 강제로 바꾸고 앞뒤 빈칸을 지워서 돌려줘요
    return TEAM_NAME_ALIASES.get(raw.strip().lower(), raw.strip())  # 팀 별명 표에서 찾고, 없으면 입력 그대로(앞뒤 빈칸만 제거) 돌려줘요


def normalize_event(raw: str) -> str:  # 여러 가지로 불리는 대회 이름을 공식 대회 이름으로 통일해 주는 함수예요
    if not raw or not isinstance(raw, str):  # 입력이 비어 있거나 글자가 아니면 그냥 글자로 바꿔서 돌려줘요
        return str(raw).strip()  # 글자로 강제로 바꾸고 앞뒤 빈칸을 지워서 돌려줘요
    return EVENT_NAME_ALIASES.get(raw.strip().lower(), raw.strip())  # 대회 별명 표에서 찾고, 없으면 입력 그대로(앞뒤 빈칸만 제거) 돌려줘요


def normalize_player(raw: str) -> str:  # 선수 이름을 공식 이름으로 통일해 주는 함수예요 (지금은 별명 표가 비어 있어서 원래 이름 그대로 돌려줘요)
    if not raw or not isinstance(raw, str):  # 입력이 비어 있거나 글자가 아니면 그냥 글자로 바꿔서 돌려줘요
        return str(raw).strip()  # 글자로 강제로 바꾸고 앞뒤 빈칸을 지워서 돌려줘요
    return PLAYER_NAME_ALIASES.get(raw.strip().lower(), raw.strip())  # 선수 별명 표에서 찾고, 없으면 입력 그대로(앞뒤 빈칸만 제거) 돌려줘요
