"""Conexão DuckDB e ingestão dos CSVs pequenos com normalização.

A ingestão é idempotente: recriar as tabelas (CREATE OR REPLACE) não duplica.
Os 4 CSVs pequenos (games, plays, players, pff) são carregados; o tracking
permanece em disco e é lido sob demanda (ver tracking.py).
"""

from __future__ import annotations

import threading
from pathlib import Path

import duckdb

from app.core.config import settings

from . import schema

_conn: duckdb.DuckDBPyConnection | None = None
_lock = threading.Lock()

# String que representa nulo nos CSVs deste dataset.
_NULLSTR = "NA"


def _read_csv_sql(path: Path, types: dict[str, str] | None = None) -> str:
    """Expressão SQL para ler um CSV do dataset tratando 'NA' como null.

    `types` força o tipo de colunas específicas (ex.: gameClock como VARCHAR,
    para evitar que "13:33" seja inferido como TIME).
    """
    safe = str(path).replace("'", "''")
    parts = [f"'{safe}'", "header=true", f"nullstr='{_NULLSTR}'", "sample_size=-1"]
    if types:
        cols = ", ".join(f"'{col}': '{dtype}'" for col, dtype in types.items())
        parts.append(f"types={{{cols}}}")
    return f"read_csv({', '.join(parts)})"


def validate_csv_columns(con: duckdb.DuckDBPyConnection, path: Path, expected: list[str]) -> None:
    """Valida que o CSV tem as colunas esperadas; erro claro caso contrário."""
    if not path.exists():
        raise FileNotFoundError(f"CSV não encontrado: {path}")
    cols = [
        row[0]
        for row in con.execute(
            f"SELECT column_name FROM (DESCRIBE SELECT * FROM {_read_csv_sql(path)})"
        ).fetchall()
    ]
    missing = [c for c in expected if c not in cols]
    if missing:
        raise ValueError(f"{path.name}: colunas ausentes {missing}. Encontradas: {cols}")


def get_connection() -> duckdb.DuckDBPyConnection:
    """Retorna a conexão DuckDB (singleton de processo), criando-a se preciso.

    Usa banco EM MEMÓRIA: as tabelas são materializadas a partir dos CSVs em
    `data/` a cada inicialização do processo. Não há arquivo `.duckdb` em disco,
    o que elimina qualquer problema de lock de arquivo entre processos.
    """
    global _conn
    if _conn is None:
        with _lock:
            if _conn is None:
                _conn = duckdb.connect(database=":memory:")
    return _conn


def _create_games(con: duckdb.DuckDBPyConnection, data_dir: Path) -> None:
    path = data_dir / "games.csv"
    validate_csv_columns(con, path, schema.GAMES_COLUMNS)
    con.execute(
        f"""
        CREATE OR REPLACE TABLE games AS
        SELECT
            gameId::BIGINT              AS game_id,
            season::INTEGER             AS season,
            week::INTEGER               AS week,
            gameDate                    AS game_date,
            gameTimeEastern             AS game_time_eastern,
            homeTeamAbbr                AS home_team,
            visitorTeamAbbr             AS visitor_team
        FROM {_read_csv_sql(path)}
        """
    )


def _create_players(con: duckdb.DuckDBPyConnection, data_dir: Path) -> None:
    path = data_dir / "players.csv"
    validate_csv_columns(con, path, schema.PLAYERS_COLUMNS)
    # height "6-4" -> polegadas via split em SQL.
    con.execute(
        f"""
        CREATE OR REPLACE TABLE players AS
        SELECT
            nflId::BIGINT               AS nfl_id,
            height                      AS height_raw,
            CASE
                WHEN height IS NULL THEN NULL
                WHEN position('-' IN height) > 0
                    THEN CAST(split_part(height, '-', 1) AS INTEGER) * 12
                       + CAST(split_part(height, '-', 2) AS INTEGER)
                ELSE TRY_CAST(height AS INTEGER)
            END::INTEGER                AS height_inches,
            weight::INTEGER             AS weight,
            birthDate                   AS birth_date,
            collegeName                 AS college,
            officialPosition            AS position,
            displayName                 AS display_name
        FROM {_read_csv_sql(path)}
        """
    )


def _create_plays(con: duckdb.DuckDBPyConnection, data_dir: Path) -> None:
    path = data_dir / "plays.csv"
    validate_csv_columns(con, path, schema.PLAYS_COLUMNS)
    # gameClock "MM:SS" -> segundos.
    con.execute(
        f"""
        CREATE OR REPLACE TABLE plays AS
        SELECT
            gameId::BIGINT              AS game_id,
            playId::BIGINT              AS play_id,
            playDescription             AS play_description,
            quarter::INTEGER            AS quarter,
            down::INTEGER               AS down,
            yardsToGo::INTEGER          AS yards_to_go,
            possessionTeam              AS possession_team,
            defensiveTeam               AS defensive_team,
            yardlineSide                AS yardline_side,
            yardlineNumber::INTEGER     AS yardline_number,
            gameClock                   AS game_clock_raw,
            CASE
                WHEN gameClock IS NULL THEN NULL
                ELSE CAST(split_part(gameClock, ':', 1) AS INTEGER) * 60
                   + CAST(split_part(gameClock, ':', 2) AS INTEGER)
            END::INTEGER                AS game_clock_seconds,
            preSnapHomeScore::INTEGER   AS pre_snap_home_score,
            preSnapVisitorScore::INTEGER AS pre_snap_visitor_score,
            passResult                  AS pass_result,
            penaltyYards::INTEGER       AS penalty_yards,
            prePenaltyPlayResult::INTEGER AS pre_penalty_play_result,
            playResult::INTEGER         AS play_result,
            absoluteYardlineNumber::INTEGER AS absolute_yardline_number,
            offenseFormation            AS offense_formation,
            personnelO                  AS personnel_offense,
            defendersInBox::INTEGER     AS defenders_in_box,
            personnelD                  AS personnel_defense,
            dropBackType                AS dropback_type,
            pff_playAction::BOOLEAN     AS play_action,
            pff_passCoverage            AS pass_coverage,
            pff_passCoverageType        AS pass_coverage_type
        FROM {_read_csv_sql(path, types={"gameClock": "VARCHAR", "playDescription": "VARCHAR"})}
        """
    )


def _create_pff(con: duckdb.DuckDBPyConnection, data_dir: Path) -> None:
    path = data_dir / "pffScoutingData.csv"
    validate_csv_columns(con, path, schema.PFF_COLUMNS)
    con.execute(
        f"""
        CREATE OR REPLACE TABLE pff AS
        SELECT
            gameId::BIGINT              AS game_id,
            playId::BIGINT              AS play_id,
            nflId::BIGINT               AS nfl_id,
            pff_role                    AS role,
            pff_positionLinedUp         AS position_lined_up,
            pff_hit::BOOLEAN            AS hit,
            pff_hurry::BOOLEAN         AS hurry,
            pff_sack::BOOLEAN          AS sack,
            pff_beatenByDefender::BOOLEAN AS beaten_by_defender,
            pff_hitAllowed::BOOLEAN    AS hit_allowed,
            pff_hurryAllowed::BOOLEAN  AS hurry_allowed,
            pff_sackAllowed::BOOLEAN   AS sack_allowed,
            pff_nflIdBlockedPlayer::BIGINT AS blocked_player_nfl_id,
            pff_blockType               AS block_type,
            pff_backFieldBlock::BOOLEAN AS backfield_block
        FROM {_read_csv_sql(path)}
        """
    )


def build_base_tables(data_dir: Path | None = None) -> None:
    """(Re)cria as tabelas base normalizadas a partir dos 4 CSVs pequenos."""
    con = get_connection()
    data = data_dir or settings.data_dir
    _create_games(con, data)
    _create_players(con, data)
    _create_plays(con, data)
    _create_pff(con, data)


def table_count(name: str) -> int:
    con = get_connection()
    return con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]  # type: ignore[index]


def close_connection() -> None:
    """Fecha a conexão (usado em testes / shutdown)."""
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
