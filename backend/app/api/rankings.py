"""Router de rankings (F7): leaderboards por métrica com snap threshold.

Aceita os filtros contextuais globais (F8): quando ativos, o ranking é
recalculado sobre as jogadas filtradas (ver services/players.py).
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.players import RankingResponse
from app.services import players as service
from app.services.filters import FilterParams, filter_params

router = APIRouter(prefix="/rankings", tags=["rankings"])


@router.get("", response_model=RankingResponse)
def get_ranking(
    metric: str = Query("pressures", description="Métrica de ordenação."),
    min_snaps: int = Query(0, ge=0, description="Mínimo de snaps (rush ou bloqueio) para entrar."),
    limit: int = Query(25, ge=1, le=200),
    filters: FilterParams = Depends(filter_params),
) -> RankingResponse:
    try:
        return service.get_ranking(
            metric=metric, min_snaps=min_snaps, limit=limit, filters=filters
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/metrics", response_model=list[str])
def list_metrics() -> list[str]:
    """Métricas de ranking disponíveis."""
    return sorted(service.RANKING_METRICS)
