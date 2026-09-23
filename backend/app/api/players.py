"""Routers de jogadores (F3): listagem/busca e ficha consolidada."""

from fastapi import APIRouter, HTTPException, Query

from app.schemas.players import PlayerListResponse, PlayerProfile
from app.services import players as service

router = APIRouter(prefix="/players", tags=["players"])


@router.get("", response_model=PlayerListResponse)
def list_players(
    search: str | None = Query(None, description="Filtro por nome (case-insensitive)."),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> PlayerListResponse:
    return service.list_players(search=search, limit=limit, offset=offset)


@router.get("/{nfl_id}", response_model=PlayerProfile)
def get_player(nfl_id: int) -> PlayerProfile:
    profile = service.get_player_profile(nfl_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Jogador {nfl_id} não encontrado.")
    return profile
