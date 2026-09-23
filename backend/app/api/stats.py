"""Router de estatísticas da camada de dados (F1).

Expõe as contagens das tabelas base/derivadas — útil para verificar que a
ingestão rodou e como sanidade rápida na demo.
"""

from fastapi import APIRouter

from app.data import loader
from app.schemas.stats import StatsResponse

router = APIRouter(tags=["infra"])


@router.get("/stats", response_model=StatsResponse)
def stats() -> StatsResponse:
    return StatsResponse(**loader.stats())
