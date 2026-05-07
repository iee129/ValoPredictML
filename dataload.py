"""
ValoPredictML 데이터셋 일괄 다운로드 스크립트

사용법:
  python dataload.py

요구사항:
  ~/.kaggle/kaggle.json 에 Kaggle API 키 필요
"""
from __future__ import annotations  # 파이썬이 좀 더 새로운 방식으로 '자료형 이름표'를 읽을 수 있게 해주는 마법 주문이에요

import shutil  # 폴더 전체를 다른 곳으로 통째로 복사할 때 쓰는 도구예요 (마치 파일 탐색기에서 폴더를 복사+붙여넣기 하는 것처럼)
import sys  # 프로그램을 도중에 멈추거나 오류 메시지를 특별한 창에 보낼 때 쓰는 도구예요
from pathlib import Path  # 파일이나 폴더 위치(경로)를 주소처럼 다루기 쉽게 해주는 도구예요

import kagglehub  # Kaggle 사이트에서 데이터 파일을 자동으로 내려받아 주는 도구예요 (마치 인터넷에서 파일을 자동 다운로드하는 것처럼)

OUTPUT_DIR = Path("data/raw/kaggle")  # 다운로드한 파일들을 저장할 폴더 주소예요 — 여기에 모든 데이터가 모입니다

# (kaggle_id, 로컬 폴더명)
# 수집 기준: agent + map + winner 필수 / K·D·A 개별 분리 / 선수-경기-맵 1행 단위
# 결측률 < 30%(핵심 스탯) / 전체 학습셋 비중 < 20% / 프로·준프로 경기만
DATASETS: list[tuple[str, str]] = [  # 내려받을 데이터 목록이에요. 마치 도서관에서 빌릴 책 목록처럼 (Kaggle 주소, 저장할 폴더 이름) 쌍으로 적혀 있어요
    # ── 핵심 소스 (대용량, 다년도) ──────────────────────────────────────────
    ("ryanluong1/valorant-champion-tour-2021-2023-data",      "vct_2021_2023"),  # 2021~2023년 VCT(발로란트 세계 대회) 경기 기록 — 가장 중요한 데이터예요
    ("ryanluong1/valorant-challengers-league-data",           "ryanluong1__valorant-challengers-league-data"),  # 챌린저스 리그(도전자 대회) 경기 기록이에요
    ("qualidea1217/valorant-pro-matches-since-april-2021",    "qualidea1217__valorant-pro-matches-since-april-2021"),  # 2021년 4월 이후의 프로 경기 기록이에요

    # ── piyush86kumar 계열 (이벤트별 상세 스탯) ─────────────────────────────
    # vct-2025-all-events 가 하위 이벤트(kickoff/stage/masters/champions)를 포함
    ("piyush86kumar/valorant-champions-tour-2024-all-events", "piyush86kumar__valorant-champions-tour-2024-all-events"),  # 2024년에 열린 모든 VCT 대회의 선수 기록이에요
    ("piyush86kumar/valorant-vct-2025-all-events",            "piyush86kumar__valorant-vct-2025-all-events"),  # 2025년에 열린 모든 VCT 대회의 선수 기록이에요

    # ── 보조 소스 (이벤트 특화) ─────────────────────────────────────────────
    ("ediashtarevin/vct-champions-2023-stats",                "ediashtarevin__vct-champions-2023-stats"),  # 2023년 챔피언스(세계 최고 대회) 특별 기록이에요

    # ── 확장 실험용 신규 소스 (piyush 동일 스키마, 2025 추가 이벤트) ──────────
    ("piyush86kumar/valorant-champions-tour-2025-paris",      "piyush86kumar__valorant-champions-tour-2025-paris"),  # 2025년 파리에서 열린 VCT 대회 기록이에요
    ("piyush86kumar/valorant-stage-2-2025-all-regions",       "piyush86kumar__valorant-stage-2-2025-all-regions"),  # 2025년 전 세계 지역에서 열린 스테이지 2 대회 기록이에요
]


def download_all() -> None:  # 목록에 있는 데이터 파일들을 하나씩 순서대로 내려받는 함수예요
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)  # 저장할 폴더가 없으면 중간 폴더까지 모두 새로 만들어요 — 이미 있으면 그냥 넘어가요

    total = len(DATASETS)  # 내려받아야 할 데이터 파일이 모두 몇 개인지 세어 저장해요
    skipped, success, failed = 0, 0, []  # 건너뜀·성공 횟수와 실패 목록을 처음엔 0개·빈 목록으로 시작해요

    for i, (kaggle_id, folder_name) in enumerate(DATASETS, 1):  # 목록을 1번부터 순서대로 꺼내며 반복해요 (마치 번호표를 뽑아 차례대로 처리하는 것처럼)
        dest = OUTPUT_DIR / folder_name  # 이 데이터 파일이 저장될 최종 폴더 주소를 만들어요
        prefix = f"[{i:2d}/{total}]"  # 화면에 보여줄 진행 번호표예요 — 예: "[ 1/ 8]" 처럼 몇 번째인지 알려줘요

        if dest.exists():  # 폴더가 이미 있으면 다시 내려받지 않고 그냥 건너뛰어요 (시간 낭비 없이!)
            print(f"{prefix} SKIP  {folder_name}")  # 건너뛴다는 메시지를 화면에 보여줘요
            skipped += 1  # 건너뜀 횟수를 1 늘려요
            continue  # 다음 데이터로 바로 넘어가요

        print(f"{prefix} DOWN  {kaggle_id} ...", flush=True)  # 내려받기를 시작한다는 메시지를 바로 화면에 보여줘요 (flush=True는 메시지를 즉시 출력하라는 뜻)
        try:
            cache_path = kagglehub.dataset_download(kaggle_id)  # Kaggle에서 데이터 파일을 임시 보관함(캐시)에 내려받아요
            shutil.copytree(cache_path, dest)  # 임시 보관함의 폴더 전체를 우리가 원하는 최종 위치로 복사해요
            print(f"{prefix} OK    → {dest}")  # 성공했다는 메시지와 저장된 위치를 화면에 보여줘요
            success += 1  # 성공 횟수를 1 늘려요
        except Exception as exc:  # 내려받기나 복사 도중 뭔가 잘못되면 여기서 잡아요
            print(f"{prefix} FAIL  {kaggle_id}: {exc}", file=sys.stderr)  # 실패 내용을 오류 전용 창(표준 에러)에 보여줘요
            failed.append((kaggle_id, str(exc)))  # 어떤 파일이 왜 실패했는지 실패 목록에 기록해요

    print(f"\n완료: {success}개 다운로드, {skipped}개 스킵", end="")  # 마지막에 몇 개 성공하고 몇 개 건너뛰었는지 결과를 보여줘요
    if failed:  # 실패한 데이터 파일이 하나라도 있으면
        print(f", {len(failed)}개 실패")  # 실패 개수도 이어서 보여줘요
        for kid, err in failed:  # 실패한 항목들을 하나씩 꺼내서
            print(f"  - {kid}: {err}", file=sys.stderr)  # 각 실패 항목의 상세 이유를 오류 전용 창에 보여줘요
        sys.exit(1)  # 숫자 1로 프로그램을 종료해요 — 자동화 시스템이 이 숫자를 보고 '오류 발생!'이라고 알 수 있어요
    else:
        print()  # 모두 성공했을 때는 줄만 바꾸고 끝내요


if __name__ == "__main__":  # 이 파일을 직접 실행했을 때만 아래 코드가 동작해요 — 다른 파일에서 가져다 쓸 때는 실행되지 않아요
    download_all()  # 데이터 파일 일괄 내려받기 함수를 불러서 시작해요
