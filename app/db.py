from __future__ import annotations  # 파이썬 버전이 낮아도 최신 방식으로 타입을 쓸 수 있게 해주는 설정

import json  # 파이썬 목록을 데이터베이스에 저장하려면 글자로 바꿔야 하고, 꺼낼 때는 다시 목록으로 바꿔야 해요 — 그 변환을 도와주는 도구
import os  # 컴퓨터에 저장된 환경 변수(비밀 설정값)를 읽어오는 도구
from datetime import datetime  # 예측을 저장할 때 "언제 저장했는지" 시각을 기록하기 위한 도구

import streamlit as st  # 데이터베이스 연결 객체를 기억해두는 메모 스티커 기능을 쓰기 위한 도구
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine  # 파이썬 코드로 데이터베이스 테이블과 컬럼을 만들 수 있게 해주는 번역기 도구들
from sqlalchemy.orm import DeclarativeBase, Session  # 데이터베이스 테이블을 파이썬 클래스처럼 다룰 수 있게 해주는 기반 도구


class Base(DeclarativeBase):  # 모든 데이터베이스 테이블 클래스가 공통으로 물려받는 부모 클래스 (SQLAlchemy 2.x 방식)
    pass


class Prediction(Base):  # 예측 결과 한 건을 데이터베이스의 한 줄로 저장하는 클래스 (predictions 테이블과 연결됨)
    __tablename__ = "predictions"  # 데이터베이스에서 이 클래스가 사용할 실제 테이블 이름

    id = Column(Integer, primary_key=True, autoincrement=True)  # 예측 기록마다 자동으로 붙는 고유 번호 (1, 2, 3... 순서로 증가)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # 예측을 저장한 시각 (전 세계 공통 UTC 시각 기준, 반드시 있어야 해요)
    map = Column(String(64), nullable=False)  # 경기가 진행된 맵 이름 (최대 64글자, 반드시 있어야 해요)
    team_a_players = Column(Text, nullable=False)  # 팀A 선수 5명의 이름 목록 — 글자로 바꿔서 저장 (반드시 있어야 해요)
    team_a_agents = Column(Text, nullable=False)  # 팀A가 고른 요원 5개 이름 목록 — 글자로 바꿔서 저장 (반드시 있어야 해요)
    team_b_players = Column(Text, nullable=False)  # 팀B 선수 5명의 이름 목록 — 글자로 바꿔서 저장 (반드시 있어야 해요)
    team_b_agents = Column(Text, nullable=False)  # 팀B가 고른 요원 5개 이름 목록 — 글자로 바꿔서 저장 (반드시 있어야 해요)
    win_probability = Column(Float, nullable=False)  # AI가 예측한 팀A의 승리 확률 (0.0이면 0%, 1.0이면 100%, 반드시 있어야 해요)
    top_factors = Column(Text, nullable=True)  # 승률에 가장 큰 영향을 미친 요소 목록 — 글자로 바꿔서 저장 (없어도 돼요)


_DEFAULT_DB_URL = "sqlite:///predictions.db"  # DATABASE_URL 환경 변수가 없을 때 쓰는 기본 데이터베이스 주소 (같은 폴더에 파일로 만들어지는 SQLite)


@st.cache_resource  # 이 함수의 결과(데이터베이스 연결)를 기억해뒀다가, 같은 주소면 다시 만들지 않고 바로 돌려주는 메모 스티커
def _build_engine(url: str):  # 데이터베이스 주소를 받아서 연결 엔진(데이터베이스와 대화할 수 있는 통로)을 만드는 내부 함수
    if url.startswith("sqlite"):  # SQLite(파일 기반 데이터베이스)는 여러 곳에서 동시에 접근할 수 있도록 특별 설정이 필요해요
        return create_engine(url, connect_args={"check_same_thread": False})  # Streamlit처럼 여러 탭이 동시에 쓰는 환경에서도 SQLite가 잘 동작하도록 설정해서 엔진 생성
    return create_engine(url, pool_pre_ping=True)  # PostgreSQL 같은 다른 데이터베이스는 연결이 살아있는지 미리 확인하면서 엔진 생성


def get_engine():  # 환경 변수에서 데이터베이스 주소를 읽어와 엔진을 반환하는 함수 (외부에서 호출하는 창구)
    url = os.getenv("DATABASE_URL", _DEFAULT_DB_URL)  # DATABASE_URL 환경 변수가 있으면 그 주소, 없으면 기본 SQLite 주소 사용
    return _build_engine(url)  # 같은 주소라면 이미 만들어둔 엔진을 재사용 (새로 만들지 않아요)


def init_db(engine) -> None:  # 데이터베이스에 아직 없는 테이블을 새로 만드는 초기화 함수
    Base.metadata.create_all(engine)  # 테이블이 없으면 새로 만들고, 이미 있으면 그냥 넘어감 (기존 데이터는 건드리지 않아요)


def save_prediction(
    engine,  # 데이터를 저장할 데이터베이스 연결 엔진
    *,  # 아래 인자들은 반드시 이름을 붙여서 호출해야 해요 (예: map_name="어센트")
    map_name: str,  # 경기가 진행된 맵 이름
    team_a_players: list[str],  # 팀A 선수 5명의 이름 목록
    team_a_agents: list[str],  # 팀A가 고른 요원 5개의 이름 목록
    team_b_players: list[str],  # 팀B 선수 5명의 이름 목록
    team_b_agents: list[str],  # 팀B가 고른 요원 5개의 이름 목록
    win_probability: float,  # AI가 예측한 팀A 승리 확률 (0.0 ~ 1.0)
    top_factors: list[dict] | None = None,  # 예측에 가장 큰 영향을 준 요소 목록 (없으면 None)
) -> None:  # 반환값 없음 (데이터베이스에 한 줄을 추가하는 것이 이 함수의 목적)
    with Session(engine) as session:  # 데이터베이스 대화 창구(세션)를 열기 — with 블록이 끝나면 자동으로 닫힘
        row = Prediction(  # 저장할 예측 결과를 담은 새 기록 객체 만들기
            created_at=datetime.utcnow(),  # 지금 이 순간의 UTC 시각을 저장 시각으로 기록
            map=map_name,  # 맵 이름 기록
            team_a_players=json.dumps(team_a_players, ensure_ascii=False),  # 팀A 선수 목록(파이썬 리스트)을 한글 그대로 글자(JSON 문자열)로 변환해서 저장
            team_a_agents=json.dumps(team_a_agents, ensure_ascii=False),  # 팀A 요원 목록을 한글 그대로 글자로 변환해서 저장
            team_b_players=json.dumps(team_b_players, ensure_ascii=False),  # 팀B 선수 목록을 한글 그대로 글자로 변환해서 저장
            team_b_agents=json.dumps(team_b_agents, ensure_ascii=False),  # 팀B 요원 목록을 한글 그대로 글자로 변환해서 저장
            win_probability=win_probability,  # 팀A 승리 확률 기록
            top_factors=json.dumps(top_factors, ensure_ascii=False) if top_factors else None,  # 기여 요소가 있으면 글자로 변환, 없으면 빈 값(NULL) 저장
        )
        session.add(row)  # 새 기록을 대화 창구에 올려놓기 (아직 실제 저장은 안 된 상태)
        session.commit()  # 올려놓은 기록을 데이터베이스에 실제로 저장 (이 순간 영구 저장됨)


def get_predictions(engine, limit: int = 50) -> list[dict]:  # 최근 예측 기록을 최신 순서로 조회하는 함수
    with Session(engine) as session:  # 데이터베이스 대화 창구 열기
        rows = (
            session.query(Prediction)  # predictions 테이블 전체를 조회 시작
            .order_by(Prediction.created_at.desc())  # 가장 최근에 저장한 기록이 맨 위에 오도록 시각 기준 내림차순 정렬
            .limit(limit)  # 최대 limit개(기본 50개)까지만 가져옴
            .all()  # 조회 실행 후 결과를 전부 리스트로 받기
        )
        return [  # 각 데이터베이스 기록을 화면에 보여주기 편한 사전(딕셔너리) 형태로 변환
            {
                "id": r.id,  # 예측 기록의 고유 번호
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M"),  # 시각을 "2026-05-06 14:30" 같은 읽기 쉬운 형태로 변환
                "map": r.map,  # 경기 맵 이름
                "team_a_players": json.loads(r.team_a_players),  # 글자로 저장된 팀A 선수 목록을 다시 파이썬 리스트로 변환
                "team_a_agents": json.loads(r.team_a_agents),  # 글자로 저장된 팀A 요원 목록을 다시 파이썬 리스트로 변환
                "team_b_players": json.loads(r.team_b_players),  # 글자로 저장된 팀B 선수 목록을 다시 파이썬 리스트로 변환
                "team_b_agents": json.loads(r.team_b_agents),  # 글자로 저장된 팀B 요원 목록을 다시 파이썬 리스트로 변환
                "win_probability": r.win_probability,  # 팀A 승리 확률 (0.0 ~ 1.0 사이 소수)
                "top_factors": json.loads(r.top_factors) if r.top_factors else [],  # 기여 요소가 있으면 리스트로 변환, 없으면 빈 리스트 반환
            }
            for r in rows  # 조회된 모든 기록에 대해 반복
        ]
