"""Configuração central da aplicação.

Lê variáveis de ambiente (opcionalmente de um arquivo .env) via pydantic-settings.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Raiz do repositório: .../projeto_nfl_data_aws
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Configurações da API, sobreponíveis por variáveis de ambiente."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="NFL_", extra="ignore")

    app_name: str = "NFL Scout API"
    version: str = "0.1.0"

    # Origens permitidas para CORS (dev do frontend Vite roda em 5173).
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Caminho para os CSVs do dataset. Aponta, por padrão, para o repositório
    # do dataset ao lado deste projeto. A camada de dados (DuckDB em memória) é
    # materializada a partir destes CSVs no startup.
    data_dir: Path = REPO_ROOT.parent / "nfl-big-data-bowl-regional-event-data" / "data"

    @property
    def tracking_dir(self) -> Path:
        return self.data_dir / "tracking"


settings = Settings()
