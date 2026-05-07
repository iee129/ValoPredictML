from __future__ import annotations  # 파이썬 버전이 낮아도 최신 방식으로 타입을 쓸 수 있게 해주는 설정

import sys  # 파이썬이 어떤 폴더에서 파일을 찾을지 알려주는 도구
from pathlib import Path  # 파일 경로를 다루는 도구 (예: "어느 폴더에 어떤 파일이 있어?" 하고 물어볼 수 있어요)

sys.path.insert(0, str(Path(__file__).parent.parent))  # 이 파일의 위쪽 폴더(프로젝트 전체 루트)를 파이썬이 제일 먼저 찾는 곳으로 등록 (다른 모듈을 불러올 수 있게)

import streamlit as st  # 웹 화면을 쉽게 만들어주는 도구 (버튼, 슬라이더, 그래프 등을 코드 몇 줄로 만들 수 있어요)
from dotenv import load_dotenv  # 숨겨둔 설정 파일(.env)에서 비밀 정보를 읽어오는 도구

load_dotenv()  # 프로젝트 폴더에 있는 .env 파일을 열어서 데이터베이스 주소 같은 비밀 정보를 프로그램에 알려줌

st.set_page_config(  # 웹 페이지의 기본 모양을 정하는 곳 (가장 먼저 실행해야 해요)
    page_title="ValoPredictML",  # 브라우저 탭에 보여줄 페이지 제목
    page_icon="🎯",  # 브라우저 탭 왼쪽에 보여줄 작은 그림(파비콘)
    layout="wide",  # 화면을 꽉 차게 넓게 쓰는 레이아웃 (기본값은 가운데 좁게 표시)
)

from app.views import guide, history, intro, predict  # noqa: E402  # 각 화면(소개, 예측, 기록, 가이드)을 담당하는 파일들을 불러옴 (페이지 설정 다음에 불러와야 해서 이 위치에 있어요)

PAGES = {  # 사이드바에 보여줄 메뉴 이름과 실제 화면 파일을 짝지어 놓은 목록
    "소개 — ValoPredictML": intro,  # '소개' 메뉴를 누르면 intro 화면을 보여줌
    "예측 — 팀 구성 + 승률": predict,  # '예측' 메뉴를 누르면 predict 화면을 보여줌
    "기록 — 예측 이력": history,  # '기록' 메뉴를 누르면 history 화면을 보여줌
    "가이드 — 역할군 + 메타": guide,  # '가이드' 메뉴를 누르면 guide 화면을 보여줌
}

st.sidebar.title("ValoPredictML")  # 왼쪽 사이드바 맨 위에 앱 이름을 크게 표시
st.sidebar.caption("발로란트 5v5 승률 예측기")  # 앱 이름 아래에 한 줄 설명을 작게 표시
st.sidebar.markdown("---")  # 제목과 메뉴 사이에 가로줄을 그어 구분

page_name = st.sidebar.radio("화면 선택", list(PAGES.keys()))  # 사이드바에 동그라미 버튼(라디오 버튼)을 만들어서 어떤 화면을 볼지 고르게 함
PAGES[page_name].render()  # 사용자가 고른 메뉴에 해당하는 화면의 render() 함수를 실행해서 화면을 보여줌
