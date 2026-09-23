"""Ponto de entrada da API FastAPI.

Instancia a aplicação, configura CORS e registra os routers.
Rodar em dev:  uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="API de análise de scout NFL (pass rush x pass protection).",
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


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"message": f"{settings.app_name} — veja /docs para a documentação da API."}
