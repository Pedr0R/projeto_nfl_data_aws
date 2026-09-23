"""Schema de resposta das contagens da camada de dados (F1)."""

from pydantic import BaseModel


class StatsResponse(BaseModel):
    games: int
    players: int
    plays: int
    pff: int
    player_play: int
    matchup: int
    player_season: int
