"""Schema de resposta para as opções de filtro (F8).

Popula os controles do painel de filtros global no frontend com os valores
possíveis de cada dimensão presentes na amostra.
"""

from __future__ import annotations

from pydantic import BaseModel


class FilterOptions(BaseModel):
    """Valores distintos disponíveis por dimensão de filtro (ordenados)."""

    weeks: list[int]
    teams: list[str]
    downs: list[int]
    quarters: list[int]
    offense_formations: list[str]
    dropback_types: list[str]
    pass_coverages: list[str]
    pass_coverage_types: list[str]
    pass_results: list[str]
    yards_to_go_min: int | None
    yards_to_go_max: int | None
