"""Testes unitários das funções de normalização (sem dependência de dados)."""

from app.data.normalize import (
    game_clock_to_seconds,
    height_to_inches,
    mirror_angle,
    mirror_x,
    mirror_y,
)
from app.data.schema import FIELD_LENGTH, FIELD_WIDTH


def test_game_clock_to_seconds():
    assert game_clock_to_seconds("13:33") == 813
    assert game_clock_to_seconds("00:05") == 5
    assert game_clock_to_seconds("15:00") == 900
    assert game_clock_to_seconds(None) is None
    assert game_clock_to_seconds("NA") is None
    assert game_clock_to_seconds("") is None


def test_height_to_inches():
    assert height_to_inches("6-4") == 76
    assert height_to_inches("5-11") == 71
    assert height_to_inches("5-6") == 66
    assert height_to_inches("74") == 74  # fallback já em polegadas
    assert height_to_inches(None) is None
    assert height_to_inches("NA") is None


def test_mirror_right_is_noop():
    assert mirror_x(37.77, "right") == 37.77
    assert mirror_y(24.22, "right") == 24.22
    assert mirror_angle(90.0, "right") == 90.0


def test_mirror_left():
    assert mirror_x(37.77, "left") == FIELD_LENGTH - 37.77
    assert mirror_y(24.22, "left") == FIELD_WIDTH - 24.22
    assert mirror_angle(90.0, "left") == 270.0
    assert mirror_angle(270.0, "left") == 90.0
    assert mirror_angle(0.0, "left") == 180.0


def test_mirror_angle_none():
    assert mirror_angle(None, "left") is None
    assert mirror_angle(None, "right") is None
