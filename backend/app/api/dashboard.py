"""Router do dashboard por persona.

Expõe `/api/dashboard/{role}`, retornando o recorte de métricas da persona
escolhida (broadcaster, scout, coach, fan).
"""

from typing import List, Union

from fastapi import APIRouter, HTTPException

from app.schemas.dashboard import (
    BroadcasterMetric,
    CoachMetric,
    FanMetric,
    RoleEnum,
    ScoutMetric,
)
from app.services.dashboard import dashboard_repository

router = APIRouter(tags=["dashboard"])


@router.get(
    "/dashboard/{role}",
    response_model=Union[
        List[BroadcasterMetric],
        List[ScoutMetric],
        List[CoachMetric],
        List[FanMetric],
    ],
)
def get_dashboard_data(role: RoleEnum):
    """Retorna as métricas da persona. 503 se o dataset não estiver carregado."""
    dashboard_repository.ensure_loaded()
    if not dashboard_repository.is_loaded:
        raise HTTPException(status_code=503, detail="Dataset do dashboard indisponível.")
    try:
        return dashboard_repository.rows_for_role(role)
    except KeyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
