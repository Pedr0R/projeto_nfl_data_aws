"""Router do dashboard por persona.

Expõe `/api/dashboard/{role}`, retornando o recorte de métricas REAIS da persona
escolhida (broadcaster, scout, coach, fan), calculado a partir do dataset.
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
from app.services import dashboard as service

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
    """Retorna as métricas reais da persona. 503 se a camada de dados não existir."""
    try:
        return service.rows_for_role(role)
    except Exception as exc:  # ex.: tabelas não construídas ainda
        raise HTTPException(
            status_code=503,
            detail=f"Camada de dados indisponível: {exc}",
        ) from exc
