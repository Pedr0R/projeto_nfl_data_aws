"""Testes de contrato do dashboard por persona (dados reais).

Requerem o dataset em disco (as personas leem das tabelas DuckDB); pulados
automaticamente se ausente.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.data import loader
from app.main import app
from app.schemas.dashboard import RoleEnum

pytestmark = pytest.mark.skipif(
    not (settings.data_dir / "plays.csv").exists(),
    reason="dataset não encontrado em settings.data_dir",
)

client = TestClient(app)

# Colunas esperadas por persona (espelham os schemas Pydantic).
EXPECTED_COLUMNS = {
    "broadcaster": {"player_name", "position", "pressures", "sacks", "pressure_rate_pct"},
    "scout": {"player_name", "position", "college", "rush_snaps", "win_rate_pct", "pressure_rate_pct"},
    "coach": {
        "player_name", "position", "block_snaps",
        "pressures_allowed", "pressure_allowed_rate_pct", "beaten_rate_pct",
    },
    "fan": {"player_name", "position", "sacks", "pressures"},
}


@pytest.fixture(scope="module", autouse=True)
def built_layer():
    loader.build_all()
    yield


@pytest.mark.parametrize("role", [r.value for r in RoleEnum])
def test_dashboard_returns_role_columns(role: str):
    resp = client.get(f"/api/dashboard/{role}")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) > 0
    for row in body:
        assert set(row.keys()) == EXPECTED_COLUMNS[role]


def test_dashboard_invalid_role_returns_422():
    resp = client.get("/api/dashboard/referee")
    assert resp.status_code == 422


def test_broadcaster_is_real_data_top_rusher():
    """Os dados vêm do dataset real: o líder de pressões é Myles Garrett."""
    resp = client.get("/api/dashboard/broadcaster")
    assert resp.status_code == 200
    rows = resp.json()
    assert rows[0]["player_name"] == "Myles Garrett"
    # ordenado por pressões desc
    pressures = [r["pressures"] for r in rows]
    assert pressures == sorted(pressures, reverse=True)


def test_coach_protection_is_ascending():
    """Coach: melhores protetores primeiro (menor taxa de pressão permitida)."""
    resp = client.get("/api/dashboard/coach")
    assert resp.status_code == 200
    rates = [r["pressure_allowed_rate_pct"] for r in resp.json()]
    assert rates == sorted(rates)
