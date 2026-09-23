"""Regras de negócio para jogadores (F3) e rankings (F7).

Consulta as tabelas derivadas (player_season, player_play, matchup) e players.
Não faz I/O de arquivo — só DuckDB.

Filtros contextuais globais (F8): quando um `FilterParams` ativo é passado, as
consultas que dependem de agregados (list_players, get_ranking e o cabeçalho da
ficha) são RECALCULADAS a partir de player_play com o WHERE de contexto aplicado
antes do GROUP BY. Sem filtros ativos, mantém-se o caminho rápido lendo a tabela
player_season pré-materializada.
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
from app.services.filters import FilterParams

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


# ---------------------------------------------------------------------------
# Reagregação por filtro (F8)
# ---------------------------------------------------------------------------
# Espelha _create_player_season (data/derived.py), mas parametrizada por um
# WHERE de contexto aplicado ANTES do GROUP BY nfl_id. Usada como subconsulta
# (CTE) quando há filtros ativos, no lugar da tabela player_season.
def _filtered_season_cte(filters: FilterParams) -> tuple[str, list]:
    """Retorna (sql_da_subquery, params) equivalente a player_season, porém só
    sobre as jogadas que passam nos filtros de contexto."""
    where_sql, params = filters.where_clause()
    where = f"WHERE {where_sql}" if where_sql else ""
    sql = f"""
        SELECT
            nfl_id,
            any_value(display_name)                          AS display_name,
            any_value(position)                              AS position,
            COUNT(*)                                         AS snaps,
            COUNT(*) FILTER (WHERE role = 'Pass Rush')       AS rush_snaps,
            COUNT(*) FILTER (WHERE role = 'Pass Rush' AND hit)   AS hits,
            COUNT(*) FILTER (WHERE role = 'Pass Rush' AND hurry) AS hurries,
            COUNT(*) FILTER (WHERE role = 'Pass Rush' AND sack)  AS sacks,
            COUNT(*) FILTER (WHERE role = 'Pass Rush' AND pressure) AS pressures,
            COUNT(*) FILTER (WHERE role = 'Pass Block')      AS block_snaps,
            COUNT(*) FILTER (WHERE role = 'Pass Block' AND hit_allowed)   AS hits_allowed,
            COUNT(*) FILTER (WHERE role = 'Pass Block' AND hurry_allowed) AS hurries_allowed,
            COUNT(*) FILTER (WHERE role = 'Pass Block' AND sack_allowed)  AS sacks_allowed,
            COUNT(*) FILTER (WHERE role = 'Pass Block' AND pressure_allowed) AS pressures_allowed,
            COUNT(*) FILTER (WHERE role = 'Pass Block' AND beaten_by_defender) AS times_beaten,
            CASE WHEN COUNT(*) FILTER (WHERE role = 'Pass Rush') > 0
                 THEN COUNT(*) FILTER (WHERE role = 'Pass Rush' AND pressure)::DOUBLE
                      / COUNT(*) FILTER (WHERE role = 'Pass Rush') END       AS pressure_rate,
            CASE WHEN COUNT(*) FILTER (WHERE role = 'Pass Block') > 0
                 THEN COUNT(*) FILTER (WHERE role = 'Pass Block' AND pressure_allowed)::DOUBLE
                      / COUNT(*) FILTER (WHERE role = 'Pass Block') END      AS pressure_allowed_rate,
            CASE WHEN COUNT(*) FILTER (WHERE role = 'Pass Block') > 0
                 THEN COUNT(*) FILTER (WHERE role = 'Pass Block' AND beaten_by_defender)::DOUBLE
                      / COUNT(*) FILTER (WHERE role = 'Pass Block') END      AS beaten_rate
        FROM player_play
        {where}
        GROUP BY nfl_id
    """
    return sql, params


def _season_source(filters: FilterParams | None) -> tuple[str, list]:
    """Fonte de dados de 'temporada': a tabela materializada quando não há
    filtros (rápido), ou uma subquery reagregada quando há (F8).

    Retorna (sql_fonte, params) onde sql_fonte pode ser usado como
    `FROM ({sql_fonte}) ps` ou, no caso sem filtro, `FROM player_season ps`.
    """
    if filters is None or not filters.is_active():
        return "player_season", []
    cte, params = _filtered_season_cte(filters)
    return f"({cte})", params


def list_players(
    search: str | None,
    limit: int,
    offset: int,
    filters: FilterParams | None = None,
) -> PlayerListResponse:
    """Lista/busca jogadores por nome (case-insensitive), respeitando F8."""
    con = get_connection()
    source, src_params = _season_source(filters)

    conds: list[str] = []
    cond_params: list = []
    if search:
        conds.append("display_name ILIKE ?")
        cond_params.append(f"%{search}%")
    where = f"WHERE {' AND '.join(conds)}" if conds else ""

    total = con.execute(
        f"SELECT COUNT(*) FROM {source} ps {where}",
        [*src_params, *cond_params],
    ).fetchone()[0]

    rows = con.execute(
        f"""
        SELECT nfl_id, display_name, position, snaps, pressures, pressures_allowed
        FROM {source} ps
        {where}
        ORDER BY snaps DESC, display_name
        LIMIT ? OFFSET ?
        """,
        [*src_params, *cond_params, limit, offset],
    ).fetchall()

    items = [
        PlayerListItem(
            nfl_id=r[0], display_name=r[1], position=r[2],
            snaps=r[3], pressures=r[4], pressures_allowed=r[5],
        )
        for r in rows
    ]
    return PlayerListResponse(total=total, items=items)


def _rusher_splits(
    con, nfl_id: int, dimension: str, filters: FilterParams | None
) -> list[SplitRow]:
    """Split de rush por uma dimensão de player_play (ex.: position_lined_up)."""
    suffix, fparams = (filters.and_suffix() if filters else ("", []))
    rows = con.execute(
        f"""
        SELECT
            {dimension}                                  AS key,
            COUNT(*)                                     AS snaps,
            COUNT(*) FILTER (WHERE pressure)             AS pressures,
            CASE WHEN COUNT(*) > 0
                 THEN COUNT(*) FILTER (WHERE pressure)::DOUBLE / COUNT(*) END AS rate
        FROM player_play
        WHERE nfl_id = ? AND role = 'Pass Rush'{suffix}
        GROUP BY {dimension}
        ORDER BY snaps DESC
        """,
        [nfl_id, *fparams],
    ).fetchall()
    return [SplitRow(key=r[0], snaps=r[1], pressures=r[2], pressure_rate=r[3]) for r in rows]


def _rusher_win_rate(
    con, nfl_id: int, filters: FilterParams | None
) -> tuple[float | None, int]:
    """Win rate do rusher via matchup: gerou pressão no par / pares com bloqueio.

    matchup não carrega contexto de jogada, então quando há filtros F8 ativos
    fazemos JOIN com player_play por (game_id, play_id) para aplicar o WHERE.
    Retorna (win_rate, n_pares).
    """
    if filters and filters.is_active():
        where_sql, fparams = filters.where_clause()
        row = con.execute(
            f"""
            SELECT
                COUNT(*)                                                       AS pairs,
                COUNT(*) FILTER (WHERE COALESCE(m.hit,false) OR COALESCE(m.hurry,false)
                                       OR COALESCE(m.sack,false))              AS wins
            FROM matchup m
            JOIN player_play pp
              ON m.game_id = pp.game_id AND m.play_id = pp.play_id
             AND m.rusher_nfl_id = pp.nfl_id
            WHERE m.rusher_nfl_id = ? AND {where_sql}
            """,
            [nfl_id, *fparams],
        ).fetchone()
    else:
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


def _block_type_usage(
    con, nfl_id: int, filters: FilterParams | None
) -> list[BlockTypeUsage]:
    suffix, fparams = (filters.and_suffix() if filters else ("", []))
    rows = con.execute(
        f"""
        SELECT block_type, COUNT(*) AS snaps,
               COUNT(*) FILTER (WHERE pressure_allowed) AS pressures_allowed
        FROM player_play
        WHERE nfl_id = ? AND role = 'Pass Block'{suffix}
        GROUP BY block_type
        ORDER BY snaps DESC
        """,
        [nfl_id, *fparams],
    ).fetchall()
    return [BlockTypeUsage(block_type=r[0], snaps=r[1], pressures_allowed=r[2]) for r in rows]


def get_player_profile(
    nfl_id: int, filters: FilterParams | None = None
) -> PlayerProfile | None:
    """Ficha consolidada; monta painel de rusher e/ou blocador conforme snaps.

    Os agregados de topo vêm de player_season (rápido) ou, com F8 ativo, de uma
    reagregação de player_play restrita ao jogador e ao contexto filtrado.
    """
    con = get_connection()

    if filters is not None and filters.is_active():
        cte, cparams = _filtered_season_cte(filters)
        row = con.execute(
            f"""
            SELECT
                ps.nfl_id, ps.display_name, ps.position, ps.snaps,
                ps.rush_snaps, ps.hits, ps.hurries, ps.sacks, ps.pressures, ps.pressure_rate,
                ps.block_snaps, ps.hits_allowed, ps.hurries_allowed, ps.sacks_allowed,
                ps.pressures_allowed, ps.pressure_allowed_rate, ps.beaten_rate,
                pl.height_inches, pl.weight, pl.college
            FROM ({cte}) ps
            LEFT JOIN players pl ON ps.nfl_id = pl.nfl_id
            WHERE ps.nfl_id = ?
            """,
            [*cparams, nfl_id],
        ).fetchone()
    else:
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
        win_rate, _ = _rusher_win_rate(con, nfl_id, filters)
        rusher = RusherProfile(
            rush_snaps=rush_snaps,
            hits=hits, hurries=hurries, sacks=sacks, pressures=pressures,
            pressure_rate=pressure_rate,
            win_rate=win_rate,
            by_alignment=_rusher_splits(con, nfl_id, "position_lined_up", filters),
            by_coverage=_rusher_splits(con, nfl_id, "pass_coverage", filters),
        )

    blocker = None
    if block_snaps and block_snaps > 0:
        blocker = BlockerProfile(
            block_snaps=block_snaps,
            hits_allowed=hits_allowed, hurries_allowed=hurries_allowed,
            sacks_allowed=sacks_allowed, pressures_allowed=pressures_allowed,
            pressure_allowed_rate=pressure_allowed_rate,
            beaten_rate=beaten_rate,
            by_block_type=_block_type_usage(con, nfl_id, filters),
        )

    return PlayerProfile(
        nfl_id=pid, display_name=name, position=position,
        height_inches=height_inches, weight=weight, college=college,
        snaps=snaps, rusher=rusher, blocker=blocker,
    )


def get_ranking(
    metric: str, min_snaps: int, limit: int, filters: FilterParams | None = None
) -> RankingResponse:
    """Ranking por métrica base, com threshold mínimo de snaps, respeitando F8."""
    if metric not in RANKING_METRICS:
        raise ValueError(
            f"Métrica inválida '{metric}'. Válidas: {sorted(RANKING_METRICS)}"
        )
    cfg = RANKING_METRICS[metric]
    col, snap_col, desc = cfg["col"], cfg["snap_col"], cfg["desc"]
    order = "DESC" if desc else "ASC"

    con = get_connection()
    source, src_params = _season_source(filters)

    total = con.execute(
        f"SELECT COUNT(*) FROM {source} ps WHERE {snap_col} >= ? AND {col} IS NOT NULL",
        [*src_params, min_snaps],
    ).fetchone()[0]

    rows = con.execute(
        f"""
        SELECT nfl_id, display_name, position, {snap_col} AS snaps, {col} AS value
        FROM {source} ps
        WHERE {snap_col} >= ? AND {col} IS NOT NULL
        ORDER BY value {order}, snaps DESC
        LIMIT ?
        """,
        [*src_params, min_snaps, limit],
    ).fetchall()

    items = [
        RankingItem(
            rank=i + 1, nfl_id=r[0], display_name=r[1],
            position=r[2], snaps=r[3], value=r[4],
        )
        for i, r in enumerate(rows)
    ]
    return RankingResponse(metric=metric, min_snaps=min_snaps, total=total, items=items)
