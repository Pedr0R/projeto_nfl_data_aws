/**
 * Estado dos filtros globais (F8) sincronizado com a URL (?week=1&team=KC...).
 *
 * Manter o estado na URL faz os filtros:
 *  - persistirem ao navegar entre telas,
 *  - serem compartilháveis (copiar link),
 *  - sobreviverem a refresh.
 *
 * Implementado sem react-router para não acoplar a fundação da SPA — usa
 * History API + evento popstate.
 */

import { useCallback, useEffect, useState } from "react";
import type { FilterParams } from "../api/types";

// Campos numéricos e booleanos para coerção correta ao ler da URL.
const NUMERIC_KEYS: (keyof FilterParams)[] = [
  "week",
  "down",
  "quarter",
  "yards_to_go_min",
  "yards_to_go_max",
];
const BOOLEAN_KEYS: (keyof FilterParams)[] = ["play_action", "pressure"];

function parseFiltersFromUrl(): FilterParams {
  const sp = new URLSearchParams(window.location.search);
  const out: FilterParams = {};
  for (const [key, raw] of sp.entries()) {
    const k = key as keyof FilterParams;
    if (NUMERIC_KEYS.includes(k)) {
      const n = Number(raw);
      if (!Number.isNaN(n)) (out[k] as number) = n;
    } else if (BOOLEAN_KEYS.includes(k)) {
      (out[k] as boolean) = raw === "true";
    } else {
      (out[k] as string) = raw;
    }
  }
  return out;
}

function writeFiltersToUrl(filters: FilterParams): void {
  const sp = new URLSearchParams(window.location.search);
  // Remove só as chaves de filtro conhecidas (preserva outros params).
  const known: (keyof FilterParams)[] = [
    "week", "team", "down", "yards_to_go_min", "yards_to_go_max", "quarter",
    "offense_formation", "dropback_type", "play_action", "pass_coverage",
    "pass_coverage_type", "pass_result", "pressure",
  ];
  known.forEach((k) => sp.delete(k));
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === null || value === "") continue;
    sp.set(key, String(value));
  }
  const qs = sp.toString();
  const url = qs ? `${window.location.pathname}?${qs}` : window.location.pathname;
  window.history.pushState({}, "", url);
}

/** Nº de filtros ativos (para badges/indicadores). */
export function countActive(filters: FilterParams): number {
  return Object.values(filters).filter(
    (v) => v !== undefined && v !== null && v !== "",
  ).length;
}

export interface UseFilters {
  filters: FilterParams;
  setFilter: <K extends keyof FilterParams>(key: K, value: FilterParams[K] | undefined) => void;
  clearFilters: () => void;
  activeCount: number;
}

export function useFilters(): UseFilters {
  const [filters, setFilters] = useState<FilterParams>(() => parseFiltersFromUrl());

  // Reflete navegação por voltar/avançar do browser.
  useEffect(() => {
    const onPop = () => setFilters(parseFiltersFromUrl());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const setFilter = useCallback(
    <K extends keyof FilterParams>(key: K, value: FilterParams[K] | undefined) => {
      setFilters((prev) => {
        const next: FilterParams = { ...prev };
        if (value === undefined || value === null || (value as unknown) === "") {
          delete next[key];
        } else {
          next[key] = value;
        }
        writeFiltersToUrl(next);
        return next;
      });
    },
    [],
  );

  const clearFilters = useCallback(() => {
    setFilters(() => {
      writeFiltersToUrl({});
      return {};
    });
  }, []);

  return { filters, setFilter, clearFilters, activeCount: countActive(filters) };
}
