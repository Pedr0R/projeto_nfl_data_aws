"""Leitura de tracking sob demanda por jogada.

O tracking (~818 MB, 122 arquivos) NÃO é ingerido no DuckDB. Cada arquivo é lido
diretamente do disco, filtrando por (gameId, playId), com as coordenadas já
normalizadas (ataque sempre para a direita). Resultados por jogada são cacheados.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.core.config import settings

from .database import get_connection
from .schema import FIELD_LENGTH, FIELD_WIDTH


def tracking_file(game_id: int) -> Path:
    return settings.tracking_dir / f"tracking_{game_id}.csv"


def _read_csv_sql(path: Path) -> str:
    safe = str(path).replace("'", "''")
    # time como VARCHAR: evita dependência de pytz para parsear timestamp com 'Z'.
    return (
        f"read_csv('{safe}', header=true, nullstr='NA', sample_size=-1, "
        "types={{'time': 'VARCHAR'}})".replace("{{", "{").replace("}}", "}")
    )


@lru_cache(maxsize=64)
def get_play_frames(game_id: int, play_id: int) -> list[dict]:
    """Retorna os frames de UMA jogada, coordenadas normalizadas p/ direita.

    Cada item é um dict com um frame de um jogador (ou da bola). A lista vem
    ordenada por frameId e nflId (bola com nfl_id=None). Resultado cacheado.
    """
    path = tracking_file(game_id)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo de tracking não encontrado: {path}")

    con = get_connection()
    rows = con.execute(
        f"""
        SELECT
            frameId::INTEGER            AS frame_id,
            nflId::BIGINT               AS nfl_id,
            jerseyNumber::INTEGER       AS jersey_number,
            team                        AS team,
            playDirection               AS play_direction,
            CASE WHEN playDirection = 'left' THEN {FIELD_LENGTH} - x ELSE x END AS x,
            CASE WHEN playDirection = 'left' THEN {FIELD_WIDTH} - y ELSE y END AS y,
            s::DOUBLE                   AS s,
            a::DOUBLE                   AS a,
            dis::DOUBLE                 AS dis,
            CASE WHEN playDirection = 'left' AND o IS NOT NULL
                 THEN (o + 180.0) - floor((o + 180.0) / 360.0) * 360.0 ELSE o END AS o,
            CASE WHEN playDirection = 'left' AND dir IS NOT NULL
                 THEN (dir + 180.0) - floor((dir + 180.0) / 360.0) * 360.0 ELSE dir END AS dir,
            event                       AS event,
            time                        AS time
        FROM {_read_csv_sql(path)}
        WHERE gameId = ? AND playId = ?
        ORDER BY frameId, nflId NULLS LAST
        """,
        [game_id, play_id],
    ).fetchall()

    cols = [
        "frame_id", "nfl_id", "jersey_number", "team", "play_direction",
        "x", "y", "s", "a", "dis", "o", "dir", "event", "time",
    ]
    return [dict(zip(cols, row)) for row in rows]


def clear_tracking_cache() -> None:
    get_play_frames.cache_clear()
