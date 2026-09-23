"""Testes de contrato e de métricas dos endpoints de jogadores (F3) e rankings (F7).

Requerem o dataset em disco; pulados automaticamente se ausente.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.data import loader
from app.main import app

pytestmark = pytest.mark.skipif(
    not (settings.data_dir / "plays.csv").exists(),
    reason="dataset não encontrado em settings.data_dir",
)

# nflIds conhecidos na amostra (verificados na Fase 2).
MYLES_GARRETT = 44813  # pass rusher
TRISTAN_WIRFS = 52421  # blocador (tackle)

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def built_layer():
    loader.build_all()
    yield


def test_list_players_basic():
    resp = client.get("/api/players", params={"limit": 10})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1_679
    assert len(body["items"]) == 10
    # ordenado por snaps desc: primeiro item tem >= snaps que o último
    assert body["items"][0]["snaps"] >= body["items"][-1]["snaps"]


def test_search_players():
    resp = client.get("/api/players", params={"search": "garrett"})
    assert resp.status_code == 200
    names = [it["display_name"] for it in resp.json()["items"]]
    assert any("Garrett" in (n or "") for n in names)


def test_player_profile_rusher():
    resp = client.get(f"/api/players/{MYLES_GARRETT}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == "Myles Garrett"
    assert body["rusher"] is not None
    r = body["rusher"]
    assert r["rush_snaps"] == 208
    assert r["pressures"] == 50
    # pressure_rate == pressures / rush_snaps
    assert r["pressure_rate"] == pytest.approx(50 / 208, rel=1e-6)
    # win_rate no intervalo [0,1]
    assert r["win_rate"] is None or 0.0 <= r["win_rate"] <= 1.0
    # splits presentes
    assert isinstance(r["by_alignment"], list) and len(r["by_alignment"]) > 0
    assert isinstance(r["by_coverage"], list) and len(r["by_coverage"]) > 0


def test_player_profile_blocker():
    resp = client.get(f"/api/players/{TRISTAN_WIRFS}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["blocker"] is not None
    b = body["blocker"]
    assert b["block_snaps"] == 309
    assert b["pressures_allowed"] == 8
    assert b["pressure_allowed_rate"] == pytest.approx(8 / 309, rel=1e-6)
    assert isinstance(b["by_block_type"], list) and len(b["by_block_type"]) > 0


def test_player_not_found():
    resp = client.get("/api/players/999999999")
    assert resp.status_code == 404


def test_ranking_pressures_threshold():
    resp = client.get("/api/rankings", params={"metric": "pressures", "min_snaps": 100, "limit": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["metric"] == "pressures"
    assert body["min_snaps"] == 100
    items = body["items"]
    assert len(items) == 5
    # ranks sequenciais e valores em ordem decrescente
    assert [it["rank"] for it in items] == [1, 2, 3, 4, 5]
    values = [it["value"] for it in items]
    assert values == sorted(values, reverse=True)
    # todos respeitam o threshold de snaps
    assert all(it["snaps"] >= 100 for it in items)
    # top de pressões na amostra é Myles Garrett
    assert items[0]["display_name"] == "Myles Garrett"


def test_ranking_allowed_rate_is_ascending():
    """Para pressão permitida, menor é melhor (ordem ascendente)."""
    resp = client.get(
        "/api/rankings",
        params={"metric": "pressure_allowed_rate", "min_snaps": 200, "limit": 5},
    )
    assert resp.status_code == 200
    values = [it["value"] for it in resp.json()["items"]]
    assert values == sorted(values)


def test_ranking_invalid_metric():
    resp = client.get("/api/rankings", params={"metric": "banana"})
    assert resp.status_code == 400


def test_ranking_metrics_list():
    resp = client.get("/api/rankings/metrics")
    assert resp.status_code == 200
    metrics = resp.json()
    assert "pressures" in metrics
    assert "beaten_rate" in metrics
