"""Regras de negócio para a visualização de jogada (F6).

Duas responsabilidades:
1. Listar jogadas que têm arquivo de tracking disponível (seletor do front).
2. Montar os frames de UMA jogada, agrupados por frameId, com nome/posição dos
   jogadores resolvidos — pronto para animar / fazer scrub na timeline.

O tracking em si é lido sob demanda por app.data.tracking (com cache); aqui só
enriquecemos e reformatamos.
"""

from __future__ import annotations

from app.data.database import get_connection
from app.data.schema import FIELD_LENGTH, FIELD_WIDTH
from app.data.tracking import get_play_frames, tracking_file
from app.schemas.tracking import (
    PlayerPosition,
    PlayMeta,
    PlayTrackingResponse,
    TrackingEvent,
    TrackingFrame,
    TrackingPlayItem,
    TrackingPlayListResponse,
)


def list_tracking_plays(
    limit: int, offset: int, search: str | None
) -> TrackingPlayListResponse:
    """Lista jogadas cujos jogos têm arquivo de tracking presente em disco.

    Sem isso o seletor poderia oferecer jogadas que não conseguimos animar.
    """
    con = get_connection()

    # Jogos que de fato têm arquivo de tracking no disco.
    game_ids = [
        row[0] for row in con.execute("SELECT DISTINCT game_id FROM games").fetchall()
    ]
    available = [gid for gid in game_ids if tracking_file(gid).exists()]
    if not available:
        return TrackingPlayListResponse(total=0, items=[])

    placeholders = ", ".join("?" for _ in available)
    where = f"WHERE p.game_id IN ({placeholders})"
    params: list = list(available)
    if search:
        where += " AND p.play_description ILIKE ?"
        params.append(f"%{search}%")

    total = con.execute(
        f"SELECT COUNT(*) FROM plays p {where}", params
    ).fetchone()[0]

    rows = con.execute(
        f"""
        SELECT
            p.game_id, p.play_id, g.week, g.home_team, g.visitor_team,
            p.possession_team, p.defensive_team, p.quarter, p.down,
            p.yards_to_go, p.play_description
        FROM plays p
        JOIN games g ON p.game_id = g.game_id
        {where}
        ORDER BY p.game_id, p.play_id
        LIMIT ? OFFSET ?
        """,
        [*params, limit, offset],
    ).fetchall()

    items = [
        TrackingPlayItem(
            game_id=r[0], play_id=r[1], week=r[2], home_team=r[3], visitor_team=r[4],
            possession_team=r[5], defensive_team=r[6], quarter=r[7], down=r[8],
            yards_to_go=r[9], play_description=r[10],
        )
        for r in rows
    ]
    return TrackingPlayListResponse(total=total, items=items)


def _play_meta(con, game_id: int, play_id: int) -> PlayMeta | None:
    row = con.execute(
        """
        SELECT
            p.game_id, p.play_id, p.play_description,
            g.home_team, g.visitor_team, p.possession_team, p.defensive_team,
            p.absolute_yardline_number, p.quarter, p.down, p.yards_to_go
        FROM plays p
        JOIN games g ON p.game_id = g.game_id
        WHERE p.game_id = ? AND p.play_id = ?
        """,
        [game_id, play_id],
    ).fetchone()
    if row is None:
        return None
    return PlayMeta(
        game_id=row[0], play_id=row[1], play_description=row[2],
        home_team=row[3], visitor_team=row[4], possession_team=row[5],
        defensive_team=row[6], absolute_yardline_number=row[7],
        quarter=row[8], down=row[9], yards_to_go=row[10],
    )


def _player_lookup(con, nfl_ids: list[int]) -> dict[int, tuple[str | None, str | None]]:
    """Mapa nfl_id -> (display_name, position) para os jogadores da jogada."""
    if not nfl_ids:
        return {}
    placeholders = ", ".join("?" for _ in nfl_ids)
    rows = con.execute(
        f"SELECT nfl_id, display_name, position FROM players WHERE nfl_id IN ({placeholders})",
        nfl_ids,
    ).fetchall()
    return {r[0]: (r[1], r[2]) for r in rows}


def get_play_tracking(game_id: int, play_id: int) -> PlayTrackingResponse | None:
    """Monta o payload completo de uma jogada para o front animar."""
    con = get_connection()
    meta = _play_meta(con, game_id, play_id)
    if meta is None:
        return None

    raw = get_play_frames(game_id, play_id)  # pode levantar FileNotFoundError
    if not raw:
        return PlayTrackingResponse(
            meta=meta, field_length=FIELD_LENGTH, field_width=FIELD_WIDTH,
            frame_count=0, events=[], frames=[],
        )

    nfl_ids = sorted({int(r["nfl_id"]) for r in raw if r["nfl_id"] is not None})
    lookup = _player_lookup(con, nfl_ids)

    # Agrupa por frameId preservando a ordem (raw já vem ordenado por frameId).
    frames_map: dict[int, TrackingFrame] = {}
    events: list[TrackingEvent] = []
    seen_events: set[str] = set()

    for r in raw:
        fid = int(r["frame_id"])
        frame = frames_map.get(fid)
        if frame is None:
            frame = TrackingFrame(frame_id=fid, event=r["event"], players=[])
            frames_map[fid] = frame
        elif frame.event is None and r["event"]:
            frame.event = r["event"]

        nid = int(r["nfl_id"]) if r["nfl_id"] is not None else None
        name, position = (None, None)
        if nid is not None and nid in lookup:
            name, position = lookup[nid]

        frame.players.append(
            PlayerPosition(
                nfl_id=nid,
                jersey_number=r["jersey_number"],
                team=r["team"],
                display_name=name,
                position=position,
                x=r["x"], y=r["y"], s=r["s"], o=r["o"], dir=r["dir"],
            )
        )

        # Registra o primeiro frame de cada tipo de evento para a timeline.
        ev = r["event"]
        if ev and ev not in seen_events:
            seen_events.add(ev)
            events.append(TrackingEvent(frame_id=fid, event=ev))

    frames = [frames_map[fid] for fid in sorted(frames_map)]
    events.sort(key=lambda e: e.frame_id)

    return PlayTrackingResponse(
        meta=meta,
        field_length=FIELD_LENGTH,
        field_width=FIELD_WIDTH,
        frame_count=len(frames),
        events=events,
        frames=frames,
    )
