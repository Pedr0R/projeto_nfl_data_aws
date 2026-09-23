"""Funções puras de normalização de campos do dataset.

Mantidas isoladas de DuckDB/pandas para serem facilmente testáveis. Também são a
referência para as expressões SQL equivalentes usadas na ingestão.
"""

from __future__ import annotations

from .schema import FIELD_LENGTH, FIELD_WIDTH


def game_clock_to_seconds(clock: str | None) -> int | None:
    """Converte `gameClock` "MM:SS" em segundos restantes no quarter.

    >>> game_clock_to_seconds("13:33")
    813
    >>> game_clock_to_seconds("00:05")
    5
    >>> game_clock_to_seconds(None)
    """
    if clock is None:
        return None
    text = clock.strip()
    if not text or text.upper() == "NA":
        return None
    parts = text.split(":")
    if len(parts) != 2:
        return None
    try:
        minutes, seconds = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    return minutes * 60 + seconds


def height_to_inches(height: str | None) -> int | None:
    """Converte altura "6-4" (pés-polegadas) em polegadas totais.

    >>> height_to_inches("6-4")
    76
    >>> height_to_inches("5-11")
    71
    >>> height_to_inches(None)
    """
    if height is None:
        return None
    text = height.strip()
    if not text or text.upper() == "NA":
        return None
    if "-" in text:
        feet_str, inch_str = text.split("-", 1)
        try:
            return int(feet_str) * 12 + int(inch_str)
        except ValueError:
            return None
    # Fallback: já em polegadas (ex.: "74").
    try:
        return int(text)
    except ValueError:
        return None


def mirror_x(x: float, play_direction: str) -> float:
    """Espelha a coordenada x quando o ataque vai para a esquerda.

    Padroniza tudo para o ataque indo para a direita.

    >>> mirror_x(37.77, "right")
    37.77
    >>> round(mirror_x(37.77, "left"), 2)
    82.23
    """
    return FIELD_LENGTH - x if play_direction == "left" else x


def mirror_y(y: float, play_direction: str) -> float:
    """Espelha a coordenada y quando o ataque vai para a esquerda.

    >>> mirror_y(24.22, "right")
    24.22
    >>> round(mirror_y(24.22, "left"), 2)
    29.08
    """
    return FIELD_WIDTH - y if play_direction == "left" else y


def mirror_angle(angle: float | None, play_direction: str) -> float | None:
    """Espelha um ângulo (o/dir, 0-360) quando o ataque vai para a esquerda.

    >>> mirror_angle(90.0, "right")
    90.0
    >>> mirror_angle(90.0, "left")
    270.0
    >>> mirror_angle(None, "left")
    """
    if angle is None:
        return None
    if play_direction != "left":
        return angle
    return (angle + 180.0) % 360.0
