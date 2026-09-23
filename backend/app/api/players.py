"""Routers de jogadores (F3): listagem/busca e ficha consolidada.

Todos os endpoints aceitam os filtros contextuais globais (F8) como query params,
via a dependency reutilizável `filter_params`.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.players import PlayerListResponse, PlayerProfile
from app.services import players as service
from app.services.filters import FilterParams, filter_params

router = APIRouter(prefix="/players", tags=["players"])


@router.get("", response_model=PlayerListResponse)
def list_players(
    search: str | None = Query(None, description="Filtro por nome (case-insensitive)."),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    filters: FilterParams = Depends(filter_params),
) -> PlayerListResponse:
    return service.list_players(search=search, limit=limit, offset=offset, filters=filters)


@router.get("/{nfl_id}", response_model=PlayerProfile)
def get_player(
    nfl_id: int,
    filters: FilterParams = Depends(filter_params),
) -> PlayerProfile:
    profile = service.get_player_profile(nfl_id, filters=filters)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Jogador {nfl_id} não encontrado.")
    return profile
