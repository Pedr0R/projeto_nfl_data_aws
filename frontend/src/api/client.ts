/**
 * Client HTTP mínimo para a API. Em dev, o Vite faz proxy de /api -> :8000
 * (ver vite.config.ts), então basta usar caminhos relativos.
 */

const API_BASE = "/api";

export async function apiGet<T>(path: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`);
  if (!resp.ok) {
    throw new Error(`GET ${path} falhou: ${resp.status}`);
  }
  return (await resp.json()) as T;
}

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
}

export function getHealth(): Promise<HealthResponse> {
  return apiGet<HealthResponse>("/health");
}
