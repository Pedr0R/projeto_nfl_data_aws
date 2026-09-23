/**
 * View de Rankings (F7) governada pelos Filtros globais (F8).
 * Demonstra a integração ponta a ponta: mudar qualquer filtro refaz o fetch
 * do ranking, que é recalculado no backend sobre a amostra filtrada.
 */

import { useEffect, useMemo, useState } from "react";
import { getRanking } from "../api/client";
import type { RankingResponse } from "../api/types";
import { useFilters } from "../hooks/useFilters";
import FiltersPanel from "./FiltersPanel";

const METRICS = [
  "pressures",
  "pressure_rate",
  "sacks",
  "hurries",
  "hits",
  "pressures_allowed",
  "pressure_allowed_rate",
  "beaten_rate",
] as const;

export default function RankingsView() {
  const controller = useFilters();
  const { filters } = controller;

  const [metric, setMetric] = useState<string>("pressures");
  const [minSnaps, setMinSnaps] = useState<number>(10);
  const [ranking, setRanking] = useState<RankingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Refaz o fetch quando métrica, min_snaps ou qualquer filtro (F8) mudar.
  const filterKey = useMemo(() => JSON.stringify(filters), [filters]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getRanking({ metric, min_snaps: minSnaps, limit: 15 }, filters)
      .then((data) => {
        if (!cancelled) setRanking(data);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [metric, minSnaps, filterKey]);

  const fmt = (v: number | null) =>
    v === null ? "—" : Number.isInteger(v) ? String(v) : v.toFixed(3);

  return (
    <>
      <FiltersPanel
        controller={controller}
        sampleLabel={ranking ? `${ranking.total} jogadores` : undefined}
      />

      <section className="card">
        <header className="ranking-header">
          <h2>Ranking</h2>
          <div className="ranking-controls">
            <label>
              Métrica{" "}
              <select value={metric} onChange={(e) => setMetric(e.target.value)}>
                {METRICS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Mín. snaps{" "}
              <input
                type="number"
                min={0}
                value={minSnaps}
                onChange={(e) => setMinSnaps(Number(e.target.value) || 0)}
                style={{ width: 64 }}
              />
            </label>
          </div>
        </header>

        {loading && <p className="muted">Carregando ranking…</p>}
        {error && <p className="badge badge-error">{error}</p>}

        {ranking && !loading && (
          <table className="ranking-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Jogador</th>
                <th>Pos</th>
                <th>Snaps</th>
                <th>{metric}</th>
              </tr>
            </thead>
            <tbody>
              {ranking.items.length === 0 && (
                <tr>
                  <td colSpan={5} className="muted">
                    Nenhum jogador para esse filtro/threshold.
                  </td>
                </tr>
              )}
              {ranking.items.map((it) => (
                <tr key={it.nfl_id}>
                  <td>{it.rank}</td>
                  <td>{it.display_name ?? "—"}</td>
                  <td>{it.position ?? "—"}</td>
                  <td>{it.snaps}</td>
                  <td>{fmt(it.value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}
