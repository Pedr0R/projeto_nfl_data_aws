"""Router de opções de filtro (F8): valores possíveis para popular os controles."""

from fastapi import APIRouter

from app.schemas.filters import FilterOptions
from app.services import filters as service

router = APIRouter(prefix="/filters", tags=["filters"])


@router.get("/options", response_model=FilterOptions)
def get_options() -> FilterOptions:
    return FilterOptions(**service.get_filter_options())
