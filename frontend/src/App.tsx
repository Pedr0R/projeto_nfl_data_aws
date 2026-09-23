import { useState } from "react";
import DashboardView from "./components/DashboardView";
import RankingsView from "./components/RankingsView";
import FieldViewer from "./FieldViewer";
import "./App.css";

type View = "dashboard" | "rankings" | "field";

const VIEWS: { id: View; label: string }[] = [
  { id: "dashboard", label: "Dashboard" },
  { id: "rankings", label: "Rankings + Filtros" },
  { id: "field", label: "Campo" },
];

export default function App() {
  const [view, setView] = useState<View>("rankings");

  return (
    <div className={`app ${view === "field" ? "app-wide" : ""}`}>
      <header className="header">
        <h1>NFL Scout</h1>
        <p className="subtitle">Análise de pass rush x proteção — Big Data Bowl 2023</p>
      </header>

      <nav className="view-tabs">
        {VIEWS.map((v) => (
          <button
            key={v.id}
            type="button"
            className={`view-tab ${view === v.id ? "view-tab-active" : ""}`}
            onClick={() => setView(v.id)}
          >
            {v.label}
          </button>
        ))}
      </nav>

      {view === "dashboard" && <DashboardView />}
      {view === "rankings" && <RankingsView />}
      {view === "field" && <FieldViewer />}
    </div>
  );
}
