"""Filtros contextuais globais (F8).

Motor reutilizável que traduz os filtros de contexto (semana, time, down,
cobertura, formação, etc.) numa cláusula `WHERE` parametrizada sobre a tabela
`player_play` — a única tabela derivada que carrega todo o contexto de
jogada/jogo (ver app/data/derived.py).

Princípios:
- **Sem SQL injection:** os nomes de coluna são de uma allowlist fixa neste
  módulo; os *valores* entram sempre como placeholders `?` (params).
- **`min_snaps` não é filtro de linha:** é um threshold pós-agregação
  (COUNT(*) >= min_snaps) e por isso NÃO entra no WHERE — fica disponível em
  `FilterParams` para os services aplicarem depois do GROUP BY.
- **`team` é dependente do papel:** rusher (role='Pass Rush') pertence ao
  `defensive_team`; blocker (role='Pass Block') ao `possession_team`. O filtro
  `team` casa "o time do jogador" de forma robusta via CASE.

Uso típico num service::

    f = FilterParams(week=3, pass_coverage="Cover 1")
    where_sql, params = f.where_clause()          # ex.: "week = ? AND pass_coverage = ?"
    con.execute(f"... WHERE role='Pass Rush' AND {where_sql}", [*params])
"""

from __future__ import annotations

from dataclasses import dataclass

# Colunas de igualdade simples em player_play (allowlist -> segurança).
# nome do campo em FilterParams -> coluna real em player_play.
_EQUALITY_COLUMNS: dict[str, str] = {
    "week": "week",
    "down": "down",
    "quarter": "quarter",
    "offense_formation": "offense_formation",
    "dropback_type": "dropback_type",
    "play_action": "play_action",
    "pass_coverage": "pass_coverage",
    "pass_coverage_type": "pass_coverage_type",
    "pass_result": "pass_result",
    "pressure": "pressure",
}


@dataclass
class FilterParams:
    """Dimensões de filtro F8 do MVP. Todos opcionais (None = sem filtro)."""

    week: int | None = None
    team: str | None = None
    down: int | None = None
    yards_to_go_min: int | None = None
    yards_to_go_max: int | None = None
    quarter: int | None = None
    offense_formation: str | None = None
    dropback_type: str | None = None
    play_action: bool | None = None
    pass_coverage: str | None = None
    pass_coverage_type: str | None = None
    pass_result: str | None = None
    pressure: bool | None = None
    # Threshold pós-agregação; NÃO entra no WHERE de linha.
    min_snaps: int = 0

    def is_active(self) -> bool:
        """Há algum filtro de contexto de linha ativo? (min_snaps não conta.)"""
        where_sql, _ = self.where_clause()
        return where_sql != ""

    def where_clause(self) -> tuple[str, list]:
        """Monta a cláusula WHERE (sem a palavra WHERE) + a lista de params.

        Retorna ("", []) quando nenhum filtro de contexto está ativo, para o
        chamador poder manter o caminho rápido (ler player_season pré-agregada).
        Todos os valores são placeholders `?`; nomes de coluna vêm de allowlist.
        """
        clauses: list[str] = []
        params: list = []

        # Igualdades simples (allowlist).
        for field, column in _EQUALITY_COLUMNS.items():
            value = getattr(self, field)
            if value is not None:
                clauses.append(f"{column} = ?")
                params.append(value)

        # Faixa de yards_to_go.
        if self.yards_to_go_min is not None:
            clauses.append("yards_to_go >= ?")
            params.append(self.yards_to_go_min)
        if self.yards_to_go_max is not None:
            clauses.append("yards_to_go <= ?")
            params.append(self.yards_to_go_max)

        # Time do jogador — depende do papel na linha (rusher/blocker).
        if self.team is not None:
            clauses.append(
                "CASE WHEN role = 'Pass Rush' THEN defensive_team "
                "ELSE possession_team END = ?"
            )
            params.append(self.team)

        return " AND ".join(clauses), params

    def and_suffix(self) -> tuple[str, list]:
        """Como where_clause, mas já prefixado com ' AND ' para concatenar num
        WHERE que já existe (ex.: "... WHERE nfl_id = ? {and_suffix}").

        Retorna ("", []) quando não há filtro ativo.
        """
        where_sql, params = self.where_clause()
        if not where_sql:
            return "", []
        return f" AND {where_sql}", params


# ---------------------------------------------------------------------------
# Dependency FastAPI reutilizável
# ---------------------------------------------------------------------------
# Importado por qualquer router que aceite os filtros globais F8. Mantém os
# nomes dos query params idênticos em toda a API (contrato único).
from fastapi import Query  # noqa: E402  (import tardio p/ manter o core sem FastAPI)


def filter_params(
    week: int | None = Query(None, description="Semana (1-8)."),
    team: str | None = Query(None, description="Sigla do time do jogador (ex.: KC)."),
    down: int | None = Query(None, ge=1, le=4),
    yards_to_go_min: int | None = Query(None, ge=0),
    yards_to_go_max: int | None = Query(None, ge=0),
    quarter: int | None = Query(None, ge=1, le=5),
    offense_formation: str | None = Query(None),
    dropback_type: str | None = Query(None),
    play_action: bool | None = Query(None),
    pass_coverage: str | None = Query(None),
    pass_coverage_type: str | None = Query(None, description="man / zone / etc."),
    pass_result: str | None = Query(None, description="C, I, S, IN, R."),
    pressure: bool | None = Query(None, description="Só jogadas com/sem pressão."),
) -> "FilterParams":
    """Dependency que monta FilterParams a partir dos query params F8.

    `min_snaps` NÃO entra aqui — é parâmetro específico de rankings/listagem e
    fica no próprio endpoint, pois é threshold de agregação, não filtro de linha.
    """
    return FilterParams(
        week=week,
        team=team,
        down=down,
        yards_to_go_min=yards_to_go_min,
        yards_to_go_max=yards_to_go_max,
        quarter=quarter,
        offense_formation=offense_formation,
        dropback_type=dropback_type,
        play_action=play_action,
        pass_coverage=pass_coverage,
        pass_coverage_type=pass_coverage_type,
        pass_result=pass_result,
        pressure=pressure,
    )


# ---------------------------------------------------------------------------
# Opções de filtro (GET /api/filters/options)
# ---------------------------------------------------------------------------
def get_filter_options() -> dict:
    """Valores distintos por dimensão, presentes na amostra (para popular os
    controles do painel F8). Lê de player_play, que já reúne contexto de
    jogada + jogo.
    """
    from app.data.database import get_connection

    con = get_connection()

    def distinct(column: str) -> list:
        rows = con.execute(
            f"SELECT DISTINCT {column} FROM player_play "
            f"WHERE {column} IS NOT NULL ORDER BY {column}"
        ).fetchall()
        return [r[0] for r in rows]

    # teams = união de possession_team e defensive_team (o mesmo time aparece
    # como ataque numas jogadas e defesa noutras).
    team_rows = con.execute(
        """
        SELECT DISTINCT team FROM (
            SELECT possession_team AS team FROM player_play WHERE possession_team IS NOT NULL
            UNION
            SELECT defensive_team AS team FROM player_play WHERE defensive_team IS NOT NULL
        ) ORDER BY team
        """
    ).fetchall()

    ytg = con.execute(
        "SELECT MIN(yards_to_go), MAX(yards_to_go) FROM player_play"
    ).fetchone()

    return {
        "weeks": distinct("week"),
        "teams": [r[0] for r in team_rows],
        "downs": distinct("down"),
        "quarters": distinct("quarter"),
        "offense_formations": distinct("offense_formation"),
        "dropback_types": distinct("dropback_type"),
        "pass_coverages": distinct("pass_coverage"),
        "pass_coverage_types": distinct("pass_coverage_type"),
        "pass_results": distinct("pass_result"),
        "yards_to_go_min": ytg[0],
        "yards_to_go_max": ytg[1],
    }
