"""Serviço de dados do dashboard por persona (Fase A).

Carrega um CSV "achatado" (uma linha por jogador com todas as métricas de persona
prontas). Se o arquivo não existir, usa um mock de fallback — útil para demo e
testes sem depender do dataset real. Na Fase B, esta camada será substituída pela
projeção das métricas reais calculadas a partir do DuckDB.
"""

from __future__ import annotations

import pandas as pd

from app.core.config import settings
from app.schemas.dashboard import ROLE_COLUMNS, RoleEnum


def _mock_dataframe() -> pd.DataFrame:
    """Dados de exemplo usados quando o CSV do dashboard não está disponível."""
    return pd.DataFrame(
        [
            {
                "player_name": "Patrick Mahomes",
                "position": "QB",
                "team": "KC",
                "college": "Texas Tech",
                "play_description": "Pass 44-yd TD to deep right",
                "catch_probability_pct": 28.4,
                "time_to_throw_sec": 2.85,
                "win_probability_pct": 74.2,
                "max_speed_mph": 19.8,
                "avg_separation_yds": 1.2,
                "yacoe": 4.1,
                "route_efficiency_index": 8.9,
                "opponent_team": "SF",
                "down_and_distance": "3rd & 8",
                "personnel_grouping": "11 Personnel",
                "blitz_pickup_rate_pct": 68.5,
                "air_yards_to_sticks": 2.3,
                "fantasy_points_projected": 24.8,
                "touchdown_likelihood_pct": 85.0,
                "highlight_moment": "Passe improvável de 40+ jardas sob pressão.",
            },
            {
                "player_name": "Justin Jefferson",
                "position": "WR",
                "team": "MIN",
                "college": "LSU",
                "play_description": "Pass complete short left for 18 yds",
                "catch_probability_pct": 62.1,
                "time_to_throw_sec": 2.30,
                "win_probability_pct": 55.0,
                "max_speed_mph": 21.2,
                "avg_separation_yds": 3.8,
                "yacoe": 7.4,
                "route_efficiency_index": 9.6,
                "opponent_team": "GB",
                "down_and_distance": "2nd & 4",
                "personnel_grouping": "12 Personnel",
                "blitz_pickup_rate_pct": 82.0,
                "air_yards_to_sticks": -1.1,
                "fantasy_points_projected": 19.5,
                "touchdown_likelihood_pct": 60.0,
                "highlight_moment": "Separação de 3.8 jardas contra cobertura mano a mano.",
            },
        ]
    )


class DashboardRepository:
    """Mantém o DataFrame do dashboard em memória e projeta por persona.

    O dado é carregado uma vez (no startup, via lifespan) e reutilizado a cada
    request. `load()` é idempotente.
    """

    def __init__(self) -> None:
        self._df: pd.DataFrame | None = None
        self._source: str = "uninitialized"

    def load(self) -> None:
        """Carrega o CSV do dashboard, ou cai no mock se o arquivo não existir."""
        csv_path = settings.dashboard_csv
        if csv_path.exists():
            self._df = pd.read_csv(csv_path)
            self._source = f"csv:{csv_path}"
        else:
            self._df = _mock_dataframe()
            self._source = "mock"

    @property
    def source(self) -> str:
        return self._source

    @property
    def is_loaded(self) -> bool:
        return self._df is not None and not self._df.empty

    def ensure_loaded(self) -> None:
        """Carrega sob demanda caso o startup (lifespan) ainda não tenha rodado.

        Torna o repositório resiliente em contextos que não disparam o lifespan
        (ex.: TestClient usado fora de um `with`).
        """
        if self._df is None:
            self.load()

    def rows_for_role(self, role: RoleEnum) -> list[dict]:
        """Retorna as linhas projetadas apenas nas colunas da persona.

        Levanta KeyError se o dataset não tiver as colunas esperadas — o router
        traduz isso num 500 com mensagem clara.
        """
        self.ensure_loaded()
        if self._df is None or self._df.empty:
            raise RuntimeError("Dataset do dashboard não carregado.")
        columns = ROLE_COLUMNS[role]
        missing = [c for c in columns if c not in self._df.columns]
        if missing:
            raise KeyError(f"Colunas ausentes no dataset para '{role.value}': {missing}")
        return self._df[columns].to_dict(orient="records")


# Instância única compartilhada pela aplicação.
dashboard_repository = DashboardRepository()
