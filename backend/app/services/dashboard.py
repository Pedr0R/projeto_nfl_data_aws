"""Serviço de dados do dashboard por persona.

Consome os dados REAIS do dataset (via tabelas derivadas em DuckDB, que por sua
vez vêm dos CSVs em `data/`). Cada persona projeta um recorte diferente das
métricas de pass rush x pass protection.

- broadcaster: top pass rushers por pressão (destaques do jogo).
- scout: avaliação técnica do rusher (win rate + taxa de pressão).
- coach: eficiência de proteção dos bloqueadores.
- fan: números diretos (sacks, pressões).
"""

from __future__ import annotations

from app.data.database import get_connection
from app.schemas.dashboard import (
    BroadcasterMetric,
    CoachMetric,
    FanMetric,
    RoleEnum,
    ScoutMetric,
)

# Mínimo de snaps para um jogador entrar em cada recorte (evita amostra pequena).
MIN_RUSH_SNAPS = 100
MIN_BLOCK_SNAPS = 150

# Quantidade de linhas por persona no dashboard.
LIMIT = 25


def _pct(value: float | None) -> float:
    """Converte taxa [0,1] em percentual arredondado; None vira 0.0."""
    return round((value or 0.0) * 100, 1)


def _broadcaster_rows(con) -> list[BroadcasterMetric]:
    rows = con.execute(
        """
        SELECT display_name, position, pressures, sacks, pressure_rate
        FROM player_season
        WHERE rush_snaps >= ?
        ORDER BY pressures DESC, pressure_rate DESC
        LIMIT ?
        """,
        [MIN_RUSH_SNAPS, LIMIT],
    ).fetchall()
    return [
        BroadcasterMetric(
            player_name=r[0] or "—",
            position=r[1] or "—",
            pressures=r[2],
            sacks=r[3],
            pressure_rate_pct=_pct(r[4]),
        )
        for r in rows
    ]


def _scout_rows(con) -> list[ScoutMetric]:
    # win rate vem do matchup (rusher gerou hit/hurry/sack no par).
    rows = con.execute(
        """
        WITH win AS (
            SELECT rusher_nfl_id AS nfl_id,
                   COUNT(*) AS pairs,
                   COUNT(*) FILTER (WHERE COALESCE(hit,false) OR COALESCE(hurry,false)
                                          OR COALESCE(sack,false)) AS wins
            FROM matchup
            GROUP BY rusher_nfl_id
        )
        SELECT ps.display_name, ps.position, pl.college, ps.rush_snaps,
               CASE WHEN w.pairs > 0 THEN w.wins::DOUBLE / w.pairs END AS win_rate,
               ps.pressure_rate
        FROM player_season ps
        LEFT JOIN players pl ON ps.nfl_id = pl.nfl_id
        LEFT JOIN win w      ON ps.nfl_id = w.nfl_id
        WHERE ps.rush_snaps >= ?
        ORDER BY win_rate DESC NULLS LAST, ps.pressure_rate DESC
        LIMIT ?
        """,
        [MIN_RUSH_SNAPS, LIMIT],
    ).fetchall()
    return [
        ScoutMetric(
            player_name=r[0] or "—",
            position=r[1] or "—",
            college=r[2] or "—",
            rush_snaps=r[3],
            win_rate_pct=_pct(r[4]),
            pressure_rate_pct=_pct(r[5]),
        )
        for r in rows
    ]


def _coach_rows(con) -> list[CoachMetric]:
    # Melhores protetores: menor taxa de pressão permitida.
    rows = con.execute(
        """
        SELECT display_name, position, block_snaps, pressures_allowed,
               pressure_allowed_rate, beaten_rate
        FROM player_season
        WHERE block_snaps >= ?
        ORDER BY pressure_allowed_rate ASC NULLS LAST
        LIMIT ?
        """,
        [MIN_BLOCK_SNAPS, LIMIT],
    ).fetchall()
    return [
        CoachMetric(
            player_name=r[0] or "—",
            position=r[1] or "—",
            block_snaps=r[2],
            pressures_allowed=r[3],
            pressure_allowed_rate_pct=_pct(r[4]),
            beaten_rate_pct=_pct(r[5]),
        )
        for r in rows
    ]


def _fan_rows(con) -> list[FanMetric]:
    rows = con.execute(
        """
        SELECT display_name, position, sacks, pressures
        FROM player_season
        WHERE rush_snaps >= ?
        ORDER BY sacks DESC, pressures DESC
        LIMIT ?
        """,
        [MIN_RUSH_SNAPS, LIMIT],
    ).fetchall()
    return [
        FanMetric(
            player_name=r[0] or "—",
            position=r[1] or "—",
            sacks=r[2],
            pressures=r[3],
        )
        for r in rows
    ]


_BUILDERS = {
    RoleEnum.BROADCASTER: _broadcaster_rows,
    RoleEnum.SCOUT: _scout_rows,
    RoleEnum.COACH: _coach_rows,
    RoleEnum.FAN: _fan_rows,
}


def rows_for_role(role: RoleEnum) -> list:
    """Retorna as linhas da persona, projetadas dos dados reais do DuckDB."""
    con = get_connection()
    return _BUILDERS[role](con)
