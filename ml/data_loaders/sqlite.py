import sqlite3
from pathlib import Path

import pandas as pd

_DEFAULT_DB = (
    Path(__file__).resolve().parents[2]
    / "data/raw/kaggle/visualize25__valorant-pro-matches-full-data/valorant.sqlite"
)


def _connect(db_path: str | None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else _DEFAULT_DB
    if not path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {path}")
    return sqlite3.connect(path)


def load_visualize25_matches(db_path: str | None = None) -> pd.DataFrame:
    """Return the Matches table (7818 rows).

    Columns: MatchID, Date, Patch, EventID, EventName, EventStage,
             Team1ID, Team2ID, Team1, Team2.
    """
    with _connect(db_path) as conn:
        return pd.read_sql_query("SELECT * FROM Matches", conn)


def load_visualize25_rounds(db_path: str | None = None) -> pd.DataFrame:
    """Return the Game_Rounds table (15531 rows).

    Columns: GameID, Team1ID, Team2ID, RoundHistory.
    """
    with _connect(db_path) as conn:
        return pd.read_sql_query("SELECT * FROM Game_Rounds", conn)


def load_visualize25_clutches(db_path: str | None = None) -> pd.DataFrame:
    """Return Game_Scoreboard (157939 rows) — no dedicated clutch table in
    source; full scoreboard used as clutch-proxy.

    Columns: GameID, PlayerID, PlayerName, TeamAbbreviation, Agent,
             ACS, Kills, Deaths, Assists, PlusMinus.
    """
    with _connect(db_path) as conn:
        return pd.read_sql_query("SELECT * FROM Game_Scoreboard", conn)
