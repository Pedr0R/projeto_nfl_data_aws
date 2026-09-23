"""Schemas de resposta para jogadores (F3) e rankings (F7)."""

from __future__ import annotations

from pydantic import BaseModel


class PlayerListItem(BaseModel):
    """Item da listagem/busca de jogadores."""

    nfl_id: int
    display_name: str | None
    position: str | None
    snaps: int
    pressures: int
    pressures_allowed: int


class PlayerListResponse(BaseModel):
    total: int
    items: list[PlayerListItem]


class SplitRow(BaseModel):
    """Uma linha de split contextual (ex.: por posição alinhada ou cobertura)."""

    key: str | None
    snaps: int
    pressures: int
    pressure_rate: float | None


class RusherProfile(BaseModel):
    """Painel de pass rusher (defesa)."""

    rush_snaps: int
    hits: int
    hurries: int
    sacks: int
    pressures: int
    pressure_rate: float | None
    win_rate: float | None  # via matchup: derrotou o bloqueador
    by_alignment: list[SplitRow]
    by_coverage: list[SplitRow]


class BlockTypeUsage(BaseModel):
    block_type: str | None
    snaps: int
    pressures_allowed: int


class BlockerProfile(BaseModel):
    """Painel de blocador (ataque)."""

    block_snaps: int
    hits_allowed: int
    hurries_allowed: int
    sacks_allowed: int
    pressures_allowed: int
    pressure_allowed_rate: float | None
    beaten_rate: float | None
    by_block_type: list[BlockTypeUsage]


class PlayerProfile(BaseModel):
    """Ficha consolidada do jogador. Painéis presentes conforme o papel."""

    nfl_id: int
    display_name: str | None
    position: str | None
    height_inches: int | None
    weight: int | None
    college: str | None
    snaps: int
    rusher: RusherProfile | None = None
    blocker: BlockerProfile | None = None


class RankingItem(BaseModel):
    rank: int
    nfl_id: int
    display_name: str | None
    position: str | None
    snaps: int
    value: float | None


class RankingResponse(BaseModel):
    metric: str
    min_snaps: int
    total: int
    items: list[RankingItem]
