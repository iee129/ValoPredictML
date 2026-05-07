from __future__ import annotations  # 파이썬 버전이 낮아도 최신 방식으로 타입을 쓸 수 있게 해주는 설정

import json  # 선수 통계가 저장된 JSON 파일(텍스트로 된 데이터 파일)을 읽기 위한 도구
from pathlib import Path  # 파일 경로를 다루는 도구
from typing import Any  # 값의 종류가 다양할 때 "뭐든 올 수 있어요"라고 표시하는 힌트

_DEFAULT_STATS: dict[str, Any] = {  # 선수 정보가 없을 때 대신 사용하는 기본 통계값 (프로 리그 평균치 기반)
    "avg_acs": 200.0,  # 평균 ACS: 한 라운드에서 얼마나 활약했는지 나타내는 점수 (200점이면 평균 수준)
    "avg_kd": 1.0,  # 평균 K/D: 적을 1명 잡을 때마다 나도 1번 죽는다는 뜻 (높을수록 좋아요)
    "avg_kast": 0.7,  # 평균 KAST: 킬·도움·생존·트레이드 중 하나라도 한 라운드 비율 (0.7 = 70%)
    "avg_adr": 130.0,  # 평균 ADR: 라운드마다 적에게 입히는 평균 피해량 (130이면 평균 수준)
    "avg_hs": 0.2,  # 평균 헤드샷 비율: 전체 킬 중 20%가 헤드샷이라는 뜻
    "max_clutch": 0.0,  # 클러치 최대 비율: 우리 팀이 불리한 상황에서 혼자 역전한 비율 (데이터 없으면 0)
    "avg_fk": 0.5,  # 평균 퍼스트 킬: 라운드 시작 후 첫 번째로 적을 처치한 횟수 평균
    "avg_fd": 0.5,  # 평균 퍼스트 데스: 라운드 시작 후 첫 번째로 죽은 횟수 평균
    "avg_assists": 2.0,  # 평균 어시스트: 팀원이 적을 처치하도록 도운 횟수 평균
}

_CACHE_PATH = Path("data/processed/player_stats.json")  # 전처리 과정에서 만들어진 선수 통계 파일의 기본 위치

_table: dict[str, dict[str, Any]] | None = None  # 한 번 읽은 선수 통계를 메모리에 보관하는 변수 (None이면 아직 읽지 않은 상태)


def build_player_stats_table(
    csv_path: str | Path | None = None,  # 통계 파일 위치를 직접 알려주고 싶을 때 쓰는 선택적 입력값
) -> dict[str, dict[str, Any]]:  # 선수 이름을 열쇠, 통계 정보를 값으로 하는 사전(딕셔너리)을 돌려주는 함수
    global _table  # 함수 밖에 있는 _table 변수를 이 함수 안에서 바꿀 수 있게 선언
    if _table is not None:  # 이미 읽어둔 데이터가 있으면 파일을 다시 읽지 않고 바로 돌려줌
        return _table  # 메모리에 저장해둔 선수 통계 사전 반환

    path = Path(csv_path) if csv_path else _CACHE_PATH  # 경로를 직접 줬으면 그 경로, 아니면 기본 경로 사용
    if not path.exists():  # 파일이 아직 없는 경우 (전처리를 아직 실행하지 않았을 때)
        _table = {}  # 빈 사전을 저장해두고
        return _table  # 빈 사전 반환 (이 경우 선수 조회 시 기본값이 사용돼요)

    with open(path, encoding="utf-8") as f:  # 한글이 깨지지 않도록 UTF-8 방식으로 파일 열기
        raw: dict[str, dict[str, Any]] = json.load(f)  # JSON 파일 전체를 선수명→통계 형태의 사전으로 읽기

    _table = {  # None(빈 값)이 있으면 기본값으로 채워서 선수 통계 사전을 정리
        name: {k: (v if v is not None else _DEFAULT_STATS.get(k, 0.0)) for k, v in stats.items()}  # 통계값이 비어있으면 기본값으로 채우기
        for name, stats in raw.items()  # 파일에서 읽은 모든 선수에 대해 반복
    }
    return _table  # 깔끔하게 정리된 선수 통계 사전 반환


def get_player_stats(player_name: str) -> dict[str, Any]:  # 선수 이름으로 통계를 찾아주고, 없으면 기본값을 돌려주는 함수
    table = build_player_stats_table()  # 선수 통계 사전을 불러오거나 메모리에 이미 있으면 바로 가져오기
    key = player_name.strip().lower()  # 앞뒤 빈칸을 지우고 소문자로 바꿔서 대소문자 차이 없이 비교할 수 있게 함
    for name, stats in table.items():  # 사전의 모든 선수 이름을 하나씩 꺼내서 비교
        if name.lower() == key:  # 소문자로 바꿔서 이름이 같으면
            return stats  # 그 선수의 통계 정보를 돌려줌
    return dict(_DEFAULT_STATS)  # 찾는 선수가 없으면 기본 통계값의 복사본을 돌려줌


def get_player_names() -> list[str]:  # 등록된 선수 이름 전체를 가나다순(알파벳순)으로 정렬해서 돌려주는 함수
    table = build_player_stats_table()  # 선수 통계 사전을 불러오거나 메모리에 이미 있으면 바로 가져오기
    return sorted(table.keys())  # 선수 이름 목록을 알파벳 순서로 정렬해서 반환
