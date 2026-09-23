/**
 * Painel de filtros globais (F8).
 *
 * Popula os controles a partir de GET /api/filters/options e reporta mudanças
 * via o hook useFilters (estado na URL). Exibe o nº de filtros ativos e permite
 * limpar tudo. O indicador de "amostra atual" (nº de itens após filtro) é
 * passado de fora, pois depende do endpoint que o consumidor está exibindo.
 */

import { useEffect, useState } from "react";
import { getFilterOptions } from "../api/client";
import type { FilterOptions, FilterParams } from "../api/types";
import type { UseFilters } from "../hooks/useFilters";

interface Props {
  controller: UseFilters;
  /** Texto opcional de amostra atual, ex.: "250 jogadores". */
  sampleLabel?: string;
}

/** Select genérico controlado por uma chave de FilterParams. */
function SelectFilter<K extends keyof FilterParams>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: FilterParams[K] | undefined;
  options: { value: string; label: string }[];
  onChange: (v: string | undefined) => void;
}) {
  return (
    <label className="filter-field">
      <span>{label}</span>
      <select
        value={value === undefined ? "" : String(value)}
        onChange={(e) => onChange(e.target.value === "" ? undefined : e.target.value)}
      >
        <option value="">Todos</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function FiltersPanel({ controller, sampleLabel }: Props) {
  const { filters, setFilter, clearFilters, activeCount } = controller;
  const [options, setOptions] = useState<FilterOptions | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getFilterOptions()
      .then(setOptions)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  const num = (v: string | undefined) => (v === undefined ? undefined : Number(v));
  const opt = (arr: (string | number)[]) =>
    arr.map((v) => ({ value: String(v), label: String(v) }));

  return (
    <section className="filters-panel card">
      <header className="filters-header">
        <h2>Filtros {activeCount > 0 && <span className="badge">{activeCount}</span>}</h2>
        <div className="filters-actions">
          {sampleLabel && <span className="muted">Amostra: {sampleLabel}</span>}
          <button type="button" onClick={clearFilters} disabled={activeCount === 0}>
            Limpar
          </button>
        </div>
      </header>

      {error && <p className="badge badge-error">Falha ao carregar filtros: {error}</p>}

      {!options && !error && <p className="muted">Carregando opções…</p>}

      {options && (
        <div className="filters-grid">
          <SelectFilter
            label="Semana"
            value={filters.week}
            options={opt(options.weeks)}
            onChange={(v) => setFilter("week", num(v))}
          />
          <SelectFilter
            label="Time"
            value={filters.team}
            options={opt(options.teams)}
            onChange={(v) => setFilter("team", v)}
          />
          <SelectFilter
            label="Down"
            value={filters.down}
            options={opt(options.downs)}
            onChange={(v) => setFilter("down", num(v))}
          />
          <SelectFilter
            label="Quarter"
            value={filters.quarter}
            options={opt(options.quarters)}
            onChange={(v) => setFilter("quarter", num(v))}
          />
          <SelectFilter
            label="Cobertura"
            value={filters.pass_coverage}
            options={opt(options.pass_coverages)}
            onChange={(v) => setFilter("pass_coverage", v)}
          />
          <SelectFilter
            label="Formação"
            value={filters.offense_formation}
            options={opt(options.offense_formations)}
            onChange={(v) => setFilter("offense_formation", v)}
          />
          <SelectFilter
            label="Dropback"
            value={filters.dropback_type}
            options={opt(options.dropback_types)}
            onChange={(v) => setFilter("dropback_type", v)}
          />
          <SelectFilter
            label="Resultado"
            value={filters.pass_result}
            options={opt(options.pass_results)}
            onChange={(v) => setFilter("pass_result", v)}
          />

          <label className="filter-field filter-check">
            <input
              type="checkbox"
              checked={filters.pressure === true}
              onChange={(e) => setFilter("pressure", e.target.checked ? true : undefined)}
            />
            <span>Só com pressão</span>
          </label>
          <label className="filter-field filter-check">
            <input
              type="checkbox"
              checked={filters.play_action === true}
              onChange={(e) => setFilter("play_action", e.target.checked ? true : undefined)}
            />
            <span>Play action</span>
          </label>
        </div>
      )}
    </section>
  );
}
