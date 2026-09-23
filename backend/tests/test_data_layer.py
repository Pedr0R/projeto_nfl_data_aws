"""Testes de sanidade da camada de dados (F1).

Requerem o dataset em disco (settings.data_dir). São pulados automaticamente se
os CSVs não estiverem presentes, para o suite rodar em qualquer ambiente.
"""

import pytest

from app.core.config import settings
from app.data import loader
from app.data.database import get_connection
from app.data.tracking import get_play_frames
from app.data.schema import FIELD_LENGTH, FIELD_WIDTH

# Pula todo o módulo se o dataset não estiver acessível.
pytestmark = pytest.mark.skipif(
    not (settings.data_dir / "plays.csv").exists(),
    reason="dataset não encontrado em settings.data_dir",
)


@pytest.fixture(scope="module", autouse=True)
def built_layer():
    """Constrói a camada uma vez para o módulo."""
    loader.build_all()
    yield


def test_reference_counts():
    """Contagens batem com os números de referência do dataset."""
    stats = loader.stats()
    assert stats["games"] == 122
    assert stats["players"] == 1_679
    assert stats["plays"] == 8_557
    assert stats["pff"] == 188_254
    # player_play é 1:1 com pff; player_season é 1:1 com players.
    assert stats["player_play"] == stats["pff"]
    assert stats["player_season"] == stats["players"]
    assert stats["matchup"] > 0


def test_game_clock_normalized():
    con = get_connection()
    row = con.execute(
        "SELECT game_clock_seconds FROM plays WHERE game_id=2021090900 AND play_id=97"
    ).fetchone()
    assert row[0] == 813  # "13:33"


def test_height_normalized():
    con = get_connection()
    row = con.execute("SELECT height_inches FROM players WHERE nfl_id=25511").fetchone()
    assert row[0] == 76  # Tom Brady, 6-4


def test_no_na_strings_leaked():
    """A string 'NA' não deve sobrar como valor (foi tratada como null)."""
    con = get_connection()
    n = con.execute("SELECT COUNT(*) FROM plays WHERE pass_coverage = 'NA'").fetchone()[0]
    assert n == 0


def test_matchup_links_valid_players():
    """Todo matchup tem bloqueador identificado."""
    con = get_connection()
    n = con.execute("SELECT COUNT(*) FROM matchup WHERE blocker_nfl_id IS NULL").fetchone()[0]
    assert n == 0


def test_pressure_rate_bounds():
    """Taxas ficam no intervalo [0, 1]."""
    con = get_connection()
    bad = con.execute(
        "SELECT COUNT(*) FROM player_season "
        "WHERE pressure_rate < 0 OR pressure_rate > 1"
    ).fetchone()[0]
    assert bad == 0


def test_tracking_frames_within_field():
    """Coordenadas normalizadas ficam dentro do campo; frame 1 tem 23 linhas (22+bola)."""
    frames = get_play_frames(2021090900, 97)
    assert len(frames) > 0
    xs = [f["x"] for f in frames]
    ys = [f["y"] for f in frames]
    assert 0 <= min(xs) and max(xs) <= FIELD_LENGTH
    assert 0 <= min(ys) and max(ys) <= FIELD_WIDTH
    frame1 = [f for f in frames if f["frame_id"] == 1]
    assert len(frame1) == 23
