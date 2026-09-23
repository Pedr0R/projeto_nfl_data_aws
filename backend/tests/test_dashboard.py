"""Testes de contrato do dashboard por persona (Fase A).

Usa o mock de fallback (não há CSV em teste), então valida a projeção por
persona e o comportamento de role inválida.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.dashboard import ROLE_COLUMNS, RoleEnum

client = TestClient(app)


@pytest.mark.parametrize("role", [r.value for r in RoleEnum])
def test_dashboard_returns_role_columns(role: str):
    resp = client.get(f"/api/dashboard/{role}")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) > 0

    expected = set(ROLE_COLUMNS[RoleEnum(role)])
    for row in body:
        assert set(row.keys()) == expected


def test_dashboard_invalid_role_returns_422():
    # RoleEnum inválida é barrada pela validação de path do FastAPI.
    resp = client.get("/api/dashboard/referee")
    assert resp.status_code == 422


def test_scout_has_expected_player():
    resp = client.get("/api/dashboard/scout")
    assert resp.status_code == 200
    names = {row["player_name"] for row in resp.json()}
    assert "Justin Jefferson" in names
