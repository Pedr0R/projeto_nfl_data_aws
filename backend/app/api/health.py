"""Router de healthcheck — usado para verificar que a API está no ar."""

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["infra"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Retorna o estado da API. Consumido pelo frontend na Fase 0."""
    return HealthResponse(status="ok", app=settings.app_name, version=settings.version)
