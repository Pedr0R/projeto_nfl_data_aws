"""Schemas de resposta para tracking / visualização de jogada (F6).

Servem o front-end da aba de campo: uma listagem de jogadas com tracking
disponível (para o seletor) e os frames de UMA jogada agrupados por frameId
(para animar / fazer scrub na timeline).
"""

from __future__ import annotations

from pydantic import BaseModel


class TrackingPlayItem(BaseModel):
    """Item do seletor de jogadas (apenas jogos com arquivo de tracking)."""

    game_id: int
    play_id: int
    week: int | None
    home_team: str | None
    visitor_team: str | None
    possession_team: str | None
    defensive_team: str | None
    quarter: int | None
    down: int | None
    yards_to_go: int | None
    play_description: str | None


class TrackingPlayListResponse(BaseModel):
    total: int
    items: list[TrackingPlayItem]


class PlayerPosition(BaseModel):
    """Posição de um jogador (ou da bola) em um frame."""

    nfl_id: int | None  # None => bola
    jersey_number: int | None
    team: str | None  # abreviação do time, ou "football" para a bola
    display_name: str | None
    position: str | None
    x: float | None
    y: float | None
    s: float | None
    o: float | None  # orientação (graus)
    dir: float | None  # direção do movimento (graus)


class TrackingFrame(BaseModel):
    """Um instante da jogada: todos os jogadores + a bola."""

    frame_id: int
    event: str | None
    players: list[PlayerPosition]


class TrackingEvent(BaseModel):
    """Marcador de evento na timeline (ball_snap, pass_forward, etc.)."""

    frame_id: int
    event: str


class PlayMeta(BaseModel):
    game_id: int
    play_id: int
    play_description: str | None
    home_team: str | None
    visitor_team: str | None
    possession_team: str | None
    defensive_team: str | None
    absolute_yardline_number: int | None
    quarter: int | None
    down: int | None
    yards_to_go: int | None


class PlayTrackingResponse(BaseModel):
    """Payload completo para animar/escanear uma jogada."""

    meta: PlayMeta
    field_length: float
    field_width: float
    frame_count: int
    events: list[TrackingEvent]
    frames: list[TrackingFrame]
