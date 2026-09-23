"""Schemas do dashboard por persona.

Cada persona (broadcaster, scout, coach, fan) enxerga um recorte diferente das
métricas. Na Fase A os dados vêm de um CSV "achatado" ou de um mock de fallback;
na Fase B estes mesmos schemas serão alimentados pelas métricas reais calculadas.
"""

from enum import Enum

from pydantic import BaseModel


class RoleEnum(str, Enum):
    """Personas suportadas pelo dashboard."""

    BROADCASTER = "broadcaster"
    SCOUT = "scout"
    COACH = "coach"
    FAN = "fan"


class BroadcasterMetric(BaseModel):
    player_name: str
    play_description: str
    catch_probability_pct: float
    time_to_throw_sec: float
    win_probability_pct: float
    max_speed_mph: float


class ScoutMetric(BaseModel):
    player_name: str
    position: str
    college: str
    avg_separation_yds: float
    yacoe: float
    route_efficiency_index: float


class CoachMetric(BaseModel):
    opponent_team: str
    down_and_distance: str
    personnel_grouping: str
    blitz_pickup_rate_pct: float
    air_yards_to_sticks: float


class FanMetric(BaseModel):
    player_name: str
    team: str
    fantasy_points_projected: float
    touchdown_likelihood_pct: float
    highlight_moment: str


# Colunas que cada persona expõe. Mantido junto dos schemas para ser a fonte
# única de verdade do recorte (usado pelo service ao projetar o DataFrame).
ROLE_COLUMNS: dict[RoleEnum, list[str]] = {
    RoleEnum.BROADCASTER: [
        "player_name",
        "play_description",
        "catch_probability_pct",
        "time_to_throw_sec",
        "win_probability_pct",
        "max_speed_mph",
    ],
    RoleEnum.SCOUT: [
        "player_name",
        "position",
        "college",
        "avg_separation_yds",
        "yacoe",
        "route_efficiency_index",
    ],
    RoleEnum.COACH: [
        "opponent_team",
        "down_and_distance",
        "personnel_grouping",
        "blitz_pickup_rate_pct",
        "air_yards_to_sticks",
    ],
    RoleEnum.FAN: [
        "player_name",
        "team",
        "fantasy_points_projected",
        "touchdown_likelihood_pct",
        "highlight_moment",
    ],
}
