import { useEffect, useMemo, useRef, useState } from "react";
import {
  fetchPlayTracking,
  fetchTrackingPlays,
  type PlayerPosition,
  type PlayTrackingResponse,
  type TrackingPlayItem,
} from "./api/client";

// Escala em pixels por jarda. O campo tem 120 x 53.3 jardas.
const PX_PER_YARD = 8;

type LoadState = "idle" | "loading" | "error";

function playLabel(p: TrackingPlayItem): string {
  const wk = p.week != null ? `S${p.week}` : "";
  const matchup = `${p.visitor_team ?? "?"} @ ${p.home_team ?? "?"}`;
  const situation =
    p.down != null && p.yards_to_go != null ? `${p.down}&${p.yards_to_go}` : "";
  const desc = p.play_description ?? "";
  const short = desc.length > 70 ? `${desc.slice(0, 70)}…` : desc;
  return [wk, matchup, situation, short].filter(Boolean).join(" · ");
}

/** Cor por papel: bola, ataque (posse) ou defesa. */
function colorFor(pl: PlayerPosition, possessionTeam: string | null): string {
  if (pl.team === "football" || pl.nfl_id == null) return "#8b5a2b"; // bola
  if (possessionTeam && pl.team === possessionTeam) return "#f59e0b"; // ataque
  return "#38bdf8"; // defesa
}

export default function FieldViewer() {
  const [plays, setPlays] = useState<TrackingPlayItem[]>([]);
  const [playsState, setPlaysState] = useState<LoadState>("loading");
  const [search, setSearch] = useState("");

  const [selected, setSelected] = useState<TrackingPlayItem | null>(null);
  const [play, setPlay] = useState<PlayTrackingResponse | null>(null);
  const [playState, setPlayState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);

  const [frameIdx, setFrameIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const rafRef = useRef<number | null>(null);
  const lastTickRef = useRef<number>(0);

  // ─── Carrega a lista de jogadas (com debounce na busca) ───
  useEffect(() => {
    let cancelled = false;
    setPlaysState("loading");
    const handle = setTimeout(() => {
      fetchTrackingPlays(search || undefined, 100)
        .then((res) => {
          if (cancelled) return;
          setPlays(res.items);
          setPlaysState("idle");
        })
        .catch((err: unknown) => {
          if (cancelled) return;
          setError(err instanceof Error ? err.message : String(err));
          setPlaysState("error");
        });
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [search]);

  // ─── Carrega os frames da jogada selecionada ───
  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    setPlayState("loading");
    setError(null);
    setPlaying(false);
    setFrameIdx(0);

    fetchPlayTracking(selected.game_id, selected.play_id)
      .then((res) => {
        if (cancelled) return;
        setPlay(res);
        setPlayState("idle");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
        setPlayState("error");
      });

    return () => {
      cancelled = true;
    };
  }, [selected]);

  // ─── Loop de animação (play/pause) ───
  useEffect(() => {
    if (!playing || !play || play.frame_count === 0) return;

    // ~10 fps é a taxa original do tracking; speed multiplica.
    const frameMs = 100 / speed;

    const step = (ts: number) => {
      if (ts - lastTickRef.current >= frameMs) {
        lastTickRef.current = ts;
        setFrameIdx((prev) => {
          if (prev >= play.frame_count - 1) {
            setPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }
      rafRef.current = requestAnimationFrame(step);
    };
    rafRef.current = requestAnimationFrame(step);

    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    };
  }, [playing, play, speed]);

  const currentFrame = play?.frames[frameIdx] ?? null;

  const fieldW = (play?.field_length ?? 120) * PX_PER_YARD;
  const fieldH = (play?.field_width ?? 53.3) * PX_PER_YARD;

  // Linhas de jarda a cada 10 jardas (endzones de 10 jardas em cada ponta).
  const yardLines = useMemo(() => {
    const lines: number[] = [];
    for (let yard = 10; yard <= 110; yard += 10) lines.push(yard);
    return lines;
  }, []);

  return (
    <div className="field-viewer">
      {/* ─── Seletor de jogada ─── */}
      <div className="fv-sidebar">
        <input
          type="text"
          className="fv-search"
          placeholder="Buscar jogada (descrição)…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {playsState === "loading" && <p className="muted">Carregando jogadas…</p>}
        {playsState === "error" && (
          <p className="badge badge-error">Erro ao listar jogadas</p>
        )}
        <ul className="fv-play-list">
          {plays.map((p) => {
            const isSel =
              selected?.game_id === p.game_id && selected?.play_id === p.play_id;
            return (
              <li key={`${p.game_id}-${p.play_id}`}>
                <button
                  type="button"
                  className={`fv-play-item ${isSel ? "fv-play-item-active" : ""}`}
                  onClick={() => setSelected(p)}
                >
                  {playLabel(p)}
                </button>
              </li>
            );
          })}
          {playsState === "idle" && plays.length === 0 && (
            <li className="muted">Nenhuma jogada encontrada.</li>
          )}
        </ul>
      </div>

      {/* ─── Campo + timeline ─── */}
      <div className="fv-main">
        {!selected && (
          <p className="muted">Selecione uma jogada à esquerda para visualizar.</p>
        )}
        {selected && playState === "loading" && (
          <p className="muted">Carregando tracking da jogada…</p>
        )}
        {error && <p className="badge badge-error">{error}</p>}

        {play && currentFrame && (
          <>
            <div className="fv-play-meta">
              <strong>
                {play.meta.visitor_team} @ {play.meta.home_team}
              </strong>
              {play.meta.play_description && (
                <span className="muted"> — {play.meta.play_description}</span>
              )}
            </div>

            <div className="fv-field-wrap">
              <svg
                className="fv-field"
                viewBox={`0 0 ${fieldW} ${fieldH}`}
                width="100%"
                preserveAspectRatio="xMidYMid meet"
              >
                {/* Gramado */}
                <rect x={0} y={0} width={fieldW} height={fieldH} fill="#1f7a3d" />
                {/* Endzones */}
                <rect x={0} y={0} width={10 * PX_PER_YARD} height={fieldH} fill="#155e2e" />
                <rect
                  x={110 * PX_PER_YARD}
                  y={0}
                  width={10 * PX_PER_YARD}
                  height={fieldH}
                  fill="#155e2e"
                />
                {/* Linhas de jarda */}
                {yardLines.map((yard) => (
                  <line
                    key={yard}
                    x1={yard * PX_PER_YARD}
                    y1={0}
                    x2={yard * PX_PER_YARD}
                    y2={fieldH}
                    stroke="#ffffff"
                    strokeOpacity={0.55}
                    strokeWidth={yard % 10 === 0 ? 2 : 1}
                  />
                ))}
                {/* Linha de scrimmage */}
                {play.meta.absolute_yardline_number != null && (
                  <line
                    x1={play.meta.absolute_yardline_number * PX_PER_YARD}
                    y1={0}
                    x2={play.meta.absolute_yardline_number * PX_PER_YARD}
                    y2={fieldH}
                    stroke="#2563eb"
                    strokeWidth={2.5}
                  />
                )}

                {/* Jogadores + bola */}
                {currentFrame.players.map((pl, i) => {
                  if (pl.x == null || pl.y == null) return null;
                  const cx = pl.x * PX_PER_YARD;
                  const cy = (play.field_width - pl.y) * PX_PER_YARD; // y invertido p/ tela
                  const isBall = pl.team === "football" || pl.nfl_id == null;
                  const fill = colorFor(pl, play.meta.possession_team);
                  const r = isBall ? 5 : 11;

                  return (
                    <g key={pl.nfl_id ?? `ball-${i}`}>
                      {/* Seta de orientação */}
                      {!isBall && pl.o != null && (
                        <line
                          x1={cx}
                          y1={cy}
                          x2={cx + Math.sin((pl.o * Math.PI) / 180) * 18}
                          y2={cy - Math.cos((pl.o * Math.PI) / 180) * 18}
                          stroke="#0f172a"
                          strokeWidth={2}
                          strokeOpacity={0.7}
                        />
                      )}
                      <circle
                        cx={cx}
                        cy={cy}
                        r={r}
                        fill={fill}
                        stroke="#0f172a"
                        strokeWidth={1.5}
                      />
                      {!isBall && pl.jersey_number != null && (
                        <text
                          x={cx}
                          y={cy + 3.5}
                          textAnchor="middle"
                          fontSize={10}
                          fontWeight={700}
                          fill="#0f172a"
                        >
                          {pl.jersey_number}
                        </text>
                      )}
                    </g>
                  );
                })}
              </svg>
            </div>

            {/* Legenda */}
            <div className="fv-legend">
              <span>
                <span className="fv-dot" style={{ background: "#f59e0b" }} /> Ataque (
                {play.meta.possession_team})
              </span>
              <span>
                <span className="fv-dot" style={{ background: "#38bdf8" }} /> Defesa (
                {play.meta.defensive_team})
              </span>
              <span>
                <span className="fv-dot" style={{ background: "#8b5a2b" }} /> Bola
              </span>
            </div>

            {/* ─── Timeline ─── */}
            <div className="fv-controls">
              <button
                type="button"
                className="fv-btn"
                onClick={() => {
                  if (frameIdx >= play.frame_count - 1) setFrameIdx(0);
                  setPlaying((p) => !p);
                }}
              >
                {playing ? "❚❚ Pausar" : "▶ Play"}
              </button>
              <button
                type="button"
                className="fv-btn"
                onClick={() => {
                  setPlaying(false);
                  setFrameIdx(0);
                }}
              >
                ⏮ Reiniciar
              </button>

              <label className="fv-speed">
                Velocidade
                <select
                  value={speed}
                  onChange={(e) => setSpeed(Number(e.target.value))}
                >
                  <option value={0.5}>0.5x</option>
                  <option value={1}>1x</option>
                  <option value={2}>2x</option>
                  <option value={4}>4x</option>
                </select>
              </label>

              <span className="fv-frame-counter">
                Frame {frameIdx + 1} / {play.frame_count}
                {currentFrame.event && (
                  <span className="fv-event-tag"> · {currentFrame.event}</span>
                )}
              </span>
            </div>

            <div className="fv-timeline-wrap">
              <input
                type="range"
                className="fv-timeline"
                min={0}
                max={Math.max(0, play.frame_count - 1)}
                value={frameIdx}
                onChange={(e) => {
                  setPlaying(false);
                  setFrameIdx(Number(e.target.value));
                }}
              />
              {/* Marcadores de eventos na timeline */}
              <div className="fv-events">
                {play.events.map((ev) => {
                  const pct =
                    play.frame_count > 1
                      ? (ev.frame_id - 1) / (play.frame_count - 1)
                      : 0;
                  return (
                    <button
                      key={`${ev.event}-${ev.frame_id}`}
                      type="button"
                      className="fv-event-marker"
                      style={{ left: `${pct * 100}%` }}
                      title={`${ev.event} (frame ${ev.frame_id})`}
                      onClick={() => {
                        setPlaying(false);
                        setFrameIdx(Math.max(0, ev.frame_id - 1));
                      }}
                    >
                      {ev.event}
                    </button>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
