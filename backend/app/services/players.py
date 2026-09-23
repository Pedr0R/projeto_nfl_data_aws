"""Regras de negócio para jogadores (F3) e rankings (F7).

Consulta as tabelas derivadas (player_season, player_play, matchup) e players.
Não faz I/O de arquivo — só DuckDB.
"""

from __future__ import annotations

from app.data.database import get_connection
from app.schemas.players import (
    BlockerProfile,
    BlockTypeUsage,
    PlayerListItem,
    PlayerListResponse,
    PlayerProfile,
    RankingItem,
    RankingResponse,
    RusherProfile,
    SplitRow,
)

# Métricas de ranking suportadas: nome -> (coluna em player_season, filtro de snaps, maior=melhor).
# `snap_col` define qual contagem de snaps usar para o threshold e para exibição.
RANKING_METRICS: dict[str, dict] = {
    "pressures": {"col": "pressures", "snap_col": "rush_snaps", "desc": True},
    "pressure_rate": {"col": "pressure_rate", "snap_col": "rush_snaps", "desc": True},
    "sacks": {"col": "sacks", "snap_col": "rush_snaps", "desc": True},
    "hurries": {"col": "hurries", "snap_col": "rush_snaps", "desc": True},
    "hits": {"col": "hits", "snap_col": "rush_snaps", "desc": True},
    "pressures_allowed": {"col": "pressures_allowed", "snap_col": "block_snaps", "desc": True},
    "pressure_allowed_rate": {
        "col": "pressure_allowed_rate",
        "snap_col": "block_snaps",
        "desc": False,  # menor é melhor para blocador
    },
    "beaten_rate": {"col": "beaten_rate", "snap_col": "block_snaps", "desc": False},
    "sacks_allowed": {"col": "sacks_allowed", "snap_col": "block_snaps", "desc": False},
}


def list_players(search: str | None, limit: int, offset: int) -> PlayerListResponse:
    """Lista/busca jogadores por nome (case-insensitive)."""
    con = get_connection()
    where = ""
    params: list = []
    if search:
        where = "WHERE display_name ILIKE ?"
        params.append(f"%{search}%")

    total = con.execute(
        f"SELECT COUNT(*) FROM player_season {where}", params
    ).fetchone()[0]

    rows = con.execute(
        f"""
        SELECT nfl_id, display_name, position, snaps, pressures, pressures_allowed
        FROM player_season
        {where}
        ORDER BY snaps DESC, display_name
        LIMIT ? OFFSET ?
        """,
        [*params, limit, offset],
    ).fetchall()

    items = [
        PlayerListItem(
            nfl_id=r[0], display_name=r[1], position=r[2],
            snaps=r[3], pressures=r[4], pressures_allowed=r[5],
        )
        for r in rows
    ]
    return PlayerListResponse(total=total, items=items)


def _rusher_splits(con, nfl_id: int, dimension: str) -> list[SplitRow]:
    """Split de rush por uma dimensão de player_play (ex.: position_lined_up)."""
    rows = con.execute(
        f"""
        SELECT
            {dimension}                                  AS key,
            COUNT(*)                                     AS snaps,
            COUNT(*) FILTER (WHERE pressure)             AS pressures,
            CASE WHEN COUNT(*) > 0
                 THEN COUNT(*) FILTER (WHERE pressure)::DOUBLE / COUNT(*) END AS rate
        FROM player_play
        WHERE nfl_id = ? AND role = 'Pass Rush'
        GROUP BY {dimension}
        ORDER BY snaps DESC
        """,
        [nfl_id],
    ).fetchall()
    return [SplitRow(key=r[0], snaps=r[1], pressures=r[2], pressure_rate=r[3]) for r in rows]


def _rusher_win_rate(con, nfl_id: int) -> tuple[float | None, int]:
    """Win rate do rusher via matchup: gerou pressão no par / pares com bloqueio.

    Retorna (win_rate, n_pares).
    """
    row = con.execute(
        """
        SELECT
            COUNT(*)                                                       AS pairs,
            COUNT(*) FILTER (WHERE COALESCE(hit,false) OR COALESCE(hurry,false)
                                   OR COALESCE(sack,false))                AS wins
        FROM matchup
        WHERE rusher_nfl_id = ?
        """,
        [nfl_id],
    ).fetchone()
    pairs, wins = row[0], row[1]
    if not pairs:
        return None, 0
    return wins / pairs, pairs


def _block_type_usage(con, nfl_id: int) -> list[BlockTypeUsage]:
    rows = con.execute(
        """
        SELECT block_type, COUNT(*) AS snaps,
               COUNT(*) FILTER (WHERE pressure_allowed) AS pressures_allowed
        FROM player_play
        WHERE nfl_id = ? AND role = 'Pass Block'
        GROUP BY block_type
        ORDER BY snaps DESC
        """,
        [nfl_id],
    ).fetchall()
    return [BlockTypeUsage(block_type=r[0], snaps=r[1], pressures_allowed=r[2]) for r in rows]


def get_player_profile(nfl_id: int) -> PlayerProfile | None:
    """Ficha consolidada; monta painel de rusher e/ou blocador conforme snaps."""
    con = get_connection()
    row = con.execute(
        """
        SELECT
            ps.nfl_id, ps.display_name, ps.position, ps.snaps,
            ps.rush_snaps, ps.hits, ps.hurries, ps.sacks, ps.pressures, ps.pressure_rate,
            ps.block_snaps, ps.hits_allowed, ps.hurries_allowed, ps.sacks_allowed,
            ps.pressures_allowed, ps.pressure_allowed_rate, ps.beaten_rate,
            pl.height_inches, pl.weight, pl.college
        FROM player_season ps
        LEFT JOIN players pl ON ps.nfl_id = pl.nfl_id
        WHERE ps.nfl_id = ?
        """,
        [nfl_id],
    ).fetchone()
    if row is None:
        return None

    (
        pid, name, position, snaps,
        rush_snaps, hits, hurries, sacks, pressures, pressure_rate,
        block_snaps, hits_allowed, hurries_allowed, sacks_allowed,
        pressures_allowed, pressure_allowed_rate, beaten_rate,
        height_inches, weight, college,
    ) = row

    rusher = None
    if rush_snaps and rush_snaps > 0:
        win_rate, _ = _rusher_win_rate(con, nfl_id)
        rusher = RusherProfile(
            rush_snaps=rush_snaps,
            hits=hits, hurries=hurries, sacks=sacks, pressures=pressures,
            pressure_rate=pressure_rate,
            win_rate=win_rate,
            by_alignment=_rusher_splits(con, nfl_id, "position_lined_up"),
            by_coverage=_rusher_splits(con, nfl_id, "pass_coverage"),
        )

    blocker = None
    if block_snaps and block_snaps > 0:
        blocker = BlockerProfile(
            block_snaps=block_snaps,
            hits_allowed=hits_allowed, hurries_allowed=hurries_allowed,
            sacks_allowed=sacks_allowed, pressures_allowed=pressures_allowed,
            pressure_allowed_rate=pressure_allowed_rate,
            beaten_rate=beaten_rate,
            by_block_type=_block_type_usage(con, nfl_id),
        )

    return PlayerProfile(
        nfl_id=pid, display_name=name, position=position,
        height_inches=height_inches, weight=weight, college=college,
        snaps=snaps, rusher=rusher, blocker=blocker,
    )


def get_ranking(metric: str, min_snaps: int, limit: int) -> RankingResponse:
    """Ranking por métrica base, com threshold mínimo de snaps."""
    if metric not in RANKING_METRICS:
        raise ValueError(
            f"Métrica inválida '{metric}'. Válidas: {sorted(RANKING_METRICS)}"
        )
    cfg = RANKING_METRICS[metric]
    col, snap_col, desc = cfg["col"], cfg["snap_col"], cfg["desc"]
    order = "DESC" if desc else "ASC"

    con = get_connection()
    total = con.execute(
        f"SELECT COUNT(*) FROM player_season WHERE {snap_col} >= ? AND {col} IS NOT NULL",
        [min_snaps],
    ).fetchone()[0]

    rows = con.execute(
        f"""
        SELECT nfl_id, display_name, position, {snap_col} AS snaps, {col} AS value
        FROM player_season
        WHERE {snap_col} >= ? AND {col} IS NOT NULL
        ORDER BY value {order}, snaps DESC
        LIMIT ?
        """,
        [min_snaps, limit],
    ).fetchall()

    items = [
        RankingItem(
            rank=i + 1, nfl_id=r[0], display_name=r[1],
            position=r[2], snaps=r[3], value=r[4],
        )
        for i, r in enumerate(rows)
    ]
    return RankingResponse(metric=metric, min_snaps=min_snaps, total=total, items=items)
