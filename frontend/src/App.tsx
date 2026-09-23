import { useEffect, useState } from "react";
import {
  fetchDashboardData,
  ROLES,
  type DashboardRow,
  type RoleEnum,
} from "./api/client";
import "./App.css";

export default function App() {
  const [activeRole, setActiveRole] = useState<RoleEnum>("broadcaster");
  const [data, setData] = useState<DashboardRow[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchDashboardData(activeRole)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activeRole]);

  return (
    <div className="app">
      <header className="header">
        <h1>NFL Analytics Hub</h1>
        <p className="subtitle">Distribuição de métricas por persona — Big Data Bowl 2023</p>
      </header>

      <nav className="tabs">
        {ROLES.map((role) => (
          <button
            key={role}
            type="button"
            className={`tab ${activeRole === role ? "tab-active" : ""}`}
            aria-pressed={activeRole === role}
            onClick={() => setActiveRole(role)}
          >
            {role}
          </button>
        ))}
      </nav>

      <main>
        {loading && <p className="muted">Buscando métricas…</p>}
        {error && (
          <div>
            <p className="badge badge-error">Erro ao carregar dados</p>
            <p className="muted">{error}</p>
            <p className="muted">
              A API está no ar? <code>cd backend; .venv\Scripts\uvicorn app.main:app --reload</code>
            </p>
          </div>
        )}

        {!loading && !error && data.length === 0 && (
          <p className="muted">Nenhum dado retornado da API.</p>
        )}

        {!loading && !error && data.length > 0 && (
          <div className="card-grid">
            {data.map((item, idx) => (
              <article key={idx} className="card">
                {Object.entries(item).map(([key, value]) => (
                  <div key={key} className="field">
                    <span className="field-label">{key.replace(/_/g, " ")}</span>
                    <span className="field-value">{String(value)}</span>
                  </div>
                ))}
              </article>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
