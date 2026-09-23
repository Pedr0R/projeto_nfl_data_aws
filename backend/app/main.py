"""Ponto de entrada da API FastAPI.

Instancia a aplicação, configura CORS e registra os routers.
Rodar em dev:  uvicorn app.main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, stats
from app.core.config import settings
from app.data import loader

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Constrói a camada de dados (F1) na inicialização, se ainda não existir."""
    try:
        loader.ensure_built()
    except FileNotFoundError:
        logger.warning(
            "Dataset não encontrado em %s — API sobe, mas endpoints de dados falharão. "
            "Defina NFL_DATA_DIR.",
            settings.data_dir,
        )
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="API de análise de scout NFL (pass rush x pass protection).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers da API (prefixo /api). Novos routers das Fases 1+ entram aqui.
app.include_router(health.router, prefix="/api")
app.include_router(stats.router, prefix="/api")


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"message": f"{settings.app_name} — veja /docs para a documentação da API."}
