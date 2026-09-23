"""Tabelas derivadas (feature store) materializadas a partir das tabelas base.

- player_play   : uma linha por jogador/jogada, com flags PFF + contexto da jogada.
- matchup       : uma linha por par bloqueador -> rusher por jogada.
- player_season : agregados por jogador na amostra (métricas base F1/F2).

Depende de build_base_tables() já ter criado games/plays/players/pff.
"""

from __future__ import annotations

from .database import get_connection


def _create_player_play(con) -> None:
    """Uma linha por (jogador, jogada): flags PFF + contexto da jogada e do jogo."""
    con.execute(
        """
        CREATE OR REPLACE TABLE player_play AS
        SELECT
            pff.game_id,
            pff.play_id,
            pff.nfl_id,
            pl.display_name,
            pl.position,
            pff.role,
            pff.position_lined_up,
            pff.hit,
            pff.hurry,
            pff.sack,
            pff.beaten_by_defender,
            pff.hit_allowed,
            pff.hurry_allowed,
            pff.sack_allowed,
            pff.blocked_player_nfl_id,
            pff.block_type,
            pff.backfield_block,
            -- flags derivadas de conveniência
            (COALESCE(pff.hit, false) OR COALESCE(pff.hurry, false)
                OR COALESCE(pff.sack, false))                    AS pressure,
            (COALESCE(pff.hit_allowed, false) OR COALESCE(pff.hurry_allowed, false)
                OR COALESCE(pff.sack_allowed, false))            AS pressure_allowed,
            -- contexto da jogada
            p.possession_team,
            p.defensive_team,
            p.down,
            p.yards_to_go,
            p.quarter,
            p.offense_formation,
            p.personnel_offense,
            p.personnel_defense,
            p.defenders_in_box,
            p.dropback_type,
            p.play_action,
            p.pass_coverage,
            p.pass_coverage_type,
            p.pass_result,
            -- contexto do jogo
            g.season,
            g.week
        FROM pff
        JOIN plays   p  ON pff.game_id = p.game_id AND pff.play_id = p.play_id
        JOIN games   g  ON pff.game_id = g.game_id
        LEFT JOIN players pl ON pff.nfl_id = pl.nfl_id
        """
    )


def _create_matchup(con) -> None:
    """Um par bloqueador -> rusher por jogada, via blocked_player_nfl_id."""
    con.execute(
        """
        CREATE OR REPLACE TABLE matchup AS
        SELECT
            b.game_id,
            b.play_id,
            b.nfl_id                       AS blocker_nfl_id,
            bp.display_name                AS blocker_name,
            b.position_lined_up            AS blocker_position,
            b.block_type,
            b.nfl_id_blocked               AS rusher_nfl_id,
            rp.display_name                AS rusher_name,
            r.position_lined_up            AS rusher_position,
            -- resultado do confronto (do ponto de vista do bloqueador)
            b.hit_allowed,
            b.hurry_allowed,
            b.sack_allowed,
            b.beaten_by_defender,
            (COALESCE(b.hit_allowed, false) OR COALESCE(b.hurry_allowed, false)
                OR COALESCE(b.sack_allowed, false))              AS pressure_allowed,
            -- resultado do rusher no par
            r.hit,
            r.hurry,
            r.sack
        FROM (
            SELECT game_id, play_id, nfl_id, position_lined_up, block_type,
                   hit_allowed, hurry_allowed, sack_allowed, beaten_by_defender,
                   blocked_player_nfl_id AS nfl_id_blocked
            FROM pff
            WHERE blocked_player_nfl_id IS NOT NULL
        ) b
        LEFT JOIN players bp ON b.nfl_id = bp.nfl_id
        LEFT JOIN players rp ON b.nfl_id_blocked = rp.nfl_id
        LEFT JOIN pff r
               ON b.game_id = r.game_id
              AND b.play_id = r.play_id
              AND b.nfl_id_blocked = r.nfl_id
        """
    )


def _create_player_season(con) -> None:
    """Agregados por jogador na amostra: produção de rush e proteção por snap."""
    con.execute(
        """
        CREATE OR REPLACE TABLE player_season AS
        WITH agg AS (
            SELECT
                nfl_id,
                any_value(display_name)                          AS display_name,
                any_value(position)                              AS position,
                COUNT(*)                                         AS snaps,
                -- rush (defesa)
                COUNT(*) FILTER (WHERE role = 'Pass Rush')       AS rush_snaps,
                COUNT(*) FILTER (WHERE role = 'Pass Rush' AND hit)   AS hits,
                COUNT(*) FILTER (WHERE role = 'Pass Rush' AND hurry) AS hurries,
                COUNT(*) FILTER (WHERE role = 'Pass Rush' AND sack)  AS sacks,
                COUNT(*) FILTER (WHERE role = 'Pass Rush' AND pressure) AS pressures,
                -- bloqueio (ataque)
                COUNT(*) FILTER (WHERE role = 'Pass Block')      AS block_snaps,
                COUNT(*) FILTER (WHERE role = 'Pass Block' AND hit_allowed)   AS hits_allowed,
                COUNT(*) FILTER (WHERE role = 'Pass Block' AND hurry_allowed) AS hurries_allowed,
                COUNT(*) FILTER (WHERE role = 'Pass Block' AND sack_allowed)  AS sacks_allowed,
                COUNT(*) FILTER (WHERE role = 'Pass Block' AND pressure_allowed) AS pressures_allowed,
                COUNT(*) FILTER (WHERE role = 'Pass Block' AND beaten_by_defender) AS times_beaten
            FROM player_play
            GROUP BY nfl_id
        )
        SELECT
            *,
            CASE WHEN rush_snaps > 0 THEN pressures::DOUBLE / rush_snaps END  AS pressure_rate,
            CASE WHEN block_snaps > 0 THEN pressures_allowed::DOUBLE / block_snaps END AS pressure_allowed_rate,
            CASE WHEN block_snaps > 0 THEN times_beaten::DOUBLE / block_snaps END AS beaten_rate
        FROM agg
        """
    )


def build_derived_tables() -> None:
    """(Re)cria player_play, matchup e player_season. Idempotente."""
    con = get_connection()
    _create_player_play(con)
    _create_matchup(con)
    _create_player_season(con)
