/**
 * Tipos espelhando o contrato da API (schemas Pydantic do backend).
 *
 * Enquanto não geramos automaticamente de /openapi.json, estes tipos são a
 * fonte de verdade manual. Ao mudar um schema no backend, atualize aqui.
 */

/** Filtros contextuais globais (F8). Todos opcionais; ausente = sem filtro. */
export interface FilterParams {
  week?: number;
  team?: string;
  down?: number;
  yards_to_go_min?: number;
  yards_to_go_max?: number;
  quarter?: number;
  offense_formation?: string;
  dropback_type?: string;
  play_action?: boolean;
  pass_coverage?: string;
  pass_coverage_type?: string;
  pass_result?: string;
  pressure?: boolean;
}

/** Resposta de GET /api/filters/options — valores possíveis por dimensão. */
export interface FilterOptions {
  weeks: number[];
  teams: string[];
  downs: number[];
  quarters: number[];
  offense_formations: string[];
  dropback_types: string[];
  pass_coverages: string[];
  pass_coverage_types: string[];
  pass_results: string[];
  yards_to_go_min: number | null;
  yards_to_go_max: number | null;
}

/** Item de GET /api/rankings. */
export interface RankingItem {
  rank: number;
  nfl_id: number;
  display_name: string | null;
  position: string | null;
  snaps: number;
  value: number | null;
}

/** Resposta de GET /api/rankings. */
export interface RankingResponse {
  metric: string;
  min_snaps: number;
  total: number;
  items: RankingItem[];
}

/** Item de GET /api/players. */
export interface PlayerListItem {
  nfl_id: number;
  display_name: string | null;
  position: string | null;
  snaps: number;
  pressures: number;
  pressures_allowed: number;
}

/** Resposta de GET /api/players. */
export interface PlayerListResponse {
  total: number;
  items: PlayerListItem[];
}
