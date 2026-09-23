import { useEffect, useState } from "react";
import { getHealth, type HealthResponse } from "./api/client";
import "./App.css";

type Status = "loading" | "ok" | "error";

export default function App() {
  const [status, setStatus] = useState<Status>("loading");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then((data) => {
        setHealth(data);
        setStatus("ok");
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err));
        setStatus("error");
      });
  }, []);

  return (
    <main className="app">
      <h1>NFL Scout</h1>
      <p className="subtitle">Análise de pass rush x proteção — Big Data Bowl 2023</p>

      <section className="card">
        <h2>Status da API</h2>
        {status === "loading" && <p className="muted">Verificando backend…</p>}
        {status === "ok" && health && (
          <p className="badge badge-ok">
            {health.app} v{health.version} — {health.status}
          </p>
        )}
        {status === "error" && (
          <div>
            <p className="badge badge-error">Backend indisponível</p>
            <p className="muted">
              Suba a API: <code>cd backend; .venv\Scripts\uvicorn app.main:app --reload</code>
            </p>
            <p className="muted">{error}</p>
          </div>
        )}
      </section>
    </main>
  );
}
