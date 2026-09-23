/**
 * Client HTTP mínimo para a API. Em dev, o Vite faz proxy de /api -> :8000
 * (ver vite.config.ts), então basta usar caminhos relativos.
 */

import type {
  FilterOptions,
  FilterParams,
  PlayerListResponse,
  RankingResponse,
} from "./types";

const API_BASE = "/api";

export async function apiGet<T>(path: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`);
  if (!resp.ok) {
    throw new Error(`GET ${path} falhou: ${resp.status}`);
  }
  return (await resp.json()) as T;
}

/**
 * Serializa filtros (F8) + extras numa query string, omitindo valores
 * nulos/indefinidos/"". Booleans viram "true"/"false".
 */
export function toQueryString(params: Record<string, unknown>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
}

export function getHealth(): Promise<HealthResponse> {
  return apiGet<HealthResponse>("/health");
}

// ─── Filtros globais (F8) ───

export function getFilterOptions(): Promise<FilterOptions> {
  return apiGet<FilterOptions>("/filters/options");
}

export function getRanking(
  opts: { metric?: string; min_snaps?: number; limit?: number },
  filters: FilterParams = {},
): Promise<RankingResponse> {
  return apiGet<RankingResponse>(
    `/rankings${toQueryString({ ...opts, ...filters })}`,
  );
}

export function getPlayers(
  opts: { search?: string; limit?: number; offset?: number },
  filters: FilterParams = {},
): Promise<PlayerListResponse> {
  return apiGet<PlayerListResponse>(
    `/players${toQueryString({ ...opts, ...filters })}`,
  );
}

// ─── Dashboard por persona ───

export type RoleEnum = "broadcaster" | "scout" | "coach" | "fan";
export const ROLES: RoleEnum[] = ["broadcaster", "scout", "coach", "fan"];
/** Uma linha do dashboard: o formato muda por persona, então tipamos genérico. */
export type DashboardRow = Record<string, string | number>;

export function fetchDashboardData(role: RoleEnum): Promise<DashboardRow[]> {
  return apiGet<DashboardRow[]>(`/dashboard/${role}`);
}

// ─── Tracking / visualização de jogada (F6) ───

export interface TrackingPlayItem {
  game_id: number;
  play_id: number;
  week: number | null;
  home_team: string | null;
  visitor_team: string | null;
  possession_team: string | null;
  defensive_team: string | null;
  quarter: number | null;
  down: number | null;
  yards_to_go: number | null;
  play_description: string | null;
}

export interface TrackingPlayListResponse {
  total: number;
  items: TrackingPlayItem[];
}

export interface PlayerPosition {
  nfl_id: number | null;
  jersey_number: number | null;
  team: string | null;
  display_name: string | null;
  position: string | null;
  x: number | null;
  y: number | null;
  s: number | null;
  o: number | null;
  dir: number | null;
}

export interface TrackingFrame {
  frame_id: number;
  event: string | null;
  players: PlayerPosition[];
}

export interface TrackingEvent {
  frame_id: number;
  event: string;
}

export interface PlayMeta {
  game_id: number;
  play_id: number;
  play_description: string | null;
  home_team: string | null;
  visitor_team: string | null;
  possession_team: string | null;
  defensive_team: string | null;
  absolute_yardline_number: number | null;
  quarter: number | null;
  down: number | null;
  yards_to_go: number | null;
}

export interface PlayTrackingResponse {
  meta: PlayMeta;
  field_length: number;
  field_width: number;
  frame_count: number;
  events: TrackingEvent[];
  frames: TrackingFrame[];
}

export function fetchTrackingPlays(
  search?: string,
  limit = 100,
): Promise<TrackingPlayListResponse> {
  return apiGet<TrackingPlayListResponse>(
    `/tracking/plays${toQueryString({ search, limit })}`,
  );
}

export function fetchPlayTracking(
  gameId: number,
  playId: number,
): Promise<PlayTrackingResponse> {
  return apiGet<PlayTrackingResponse>(`/tracking/${gameId}/${playId}`);
}
