"""Schemas do dashboard por persona.

Cada persona (broadcaster, scout, coach, fan) enxerga um recorte diferente das
métricas REAIS do dataset (pass rush x pass protection, Big Data Bowl 2023).
Os dados vêm das tabelas derivadas em DuckDB (player_season, matchup), calculadas
a partir dos CSVs em `data/`.
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
    """Narração: destaques de pressão para contar a história do jogo."""

    player_name: str
    position: str
    pressures: int
    sacks: int
    pressure_rate_pct: float


class ScoutMetric(BaseModel):
    """Scout: avaliação técnica do pass rusher."""

    player_name: str
    position: str
    college: str
    rush_snaps: int
    win_rate_pct: float
    pressure_rate_pct: float


class CoachMetric(BaseModel):
    """Coach: eficiência de proteção (pass protection) dos bloqueadores."""

    player_name: str
    position: str
    block_snaps: int
    pressures_allowed: int
    pressure_allowed_rate_pct: float
    beaten_rate_pct: float


class FanMetric(BaseModel):
    """Fã: números diretos e chamativos."""

    player_name: str
    position: str
    sacks: int
    pressures: int
