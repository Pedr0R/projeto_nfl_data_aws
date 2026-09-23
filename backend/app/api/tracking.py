"""Router de tracking / visualização de jogada (F6).

Endpoints:
- GET /tracking/plays          -> jogadas com tracking disponível (seletor).
- GET /tracking/{gid}/{pid}    -> frames de uma jogada para animar / scrub.
"""

from fastapi import APIRouter, HTTPException, Query

from app.schemas.tracking import PlayTrackingResponse, TrackingPlayListResponse
from app.services import tracking as service

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.get("/plays", response_model=TrackingPlayListResponse)
def list_plays(
    search: str | None = Query(None, description="Filtro por descrição da jogada."),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> TrackingPlayListResponse:
    return service.list_tracking_plays(limit=limit, offset=offset, search=search)


@router.get("/{game_id}/{play_id}", response_model=PlayTrackingResponse)
def get_play(game_id: int, play_id: int) -> PlayTrackingResponse:
    try:
        result = service.get_play_tracking(game_id, play_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Jogada ({game_id}, {play_id}) não encontrada.",
        )
    return result
