# NFL Scout — Plataforma de Análise de Pass Rush x Proteção

Ferramenta de scout sobre o dataset **NFL Big Data Bowl 2023** (temporada 2021,
semanas 1-8). Backend em **FastAPI**, frontend em **React + TypeScript**, camada
de dados em **Python + pandas + DuckDB**.

- Design das features: [`features/features_gerais.md`](features/features_gerais.md)
- Plano de implementação: [`features/plano_implementacao.md`](features/plano_implementacao.md)

## Estrutura

```
projeto_nfl_data_aws/
├── backend/     # API FastAPI (Python)
├── frontend/    # SPA React + TypeScript (Vite)
├── data/        # CSVs do dataset (NÃO versionado — ver abaixo)
└── features/    # documentação (design + plano)
```

## Pré-requisitos

- Python 3.11+ (testado com 3.13)
- Node.js 18+ (testado com 22) e npm

## Dados

O dataset (~818 MB de tracking) **não é versionado**. O backend, por padrão,
aponta para o repositório do dataset ao lado deste projeto:

```
<pasta-pai>/
├── projeto_nfl_data_aws/                    (este repo)
└── nfl-big-data-bowl-regional-event-data/
    └── data/                                (games.csv, plays.csv, ...)
```

Para usar outro caminho, defina a variável de ambiente `NFL_DATA_DIR`
(ver `backend/.env.example`). Os dados só são efetivamente usados a partir da
Fase 1.

## Backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# rodar em dev (porta 8000)
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

- API: http://localhost:8000
- Docs (OpenAPI/Swagger): http://localhost:8000/docs
- Healthcheck: http://localhost:8000/api/health

Testes:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

## Frontend

```powershell
cd frontend
npm install

# rodar em dev (porta 5173)
npm run dev
```

- App: http://localhost:5173
- Em dev, o Vite faz proxy de `/api` para o backend em `http://localhost:8000`
  (ver `frontend/vite.config.ts`), então rode os dois em paralelo.

Build de produção:

```powershell
cd frontend
npm run build
```

## Camada de dados (F1)

A camada normalizada + derivada é materializada em DuckDB a partir dos CSVs.
Construir/reconstruir (idempotente):

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.data.loader --stats
```

Tabelas geradas: `games`, `players`, `plays`, `pff` (base normalizada) e
`player_play`, `matchup`, `player_season` (derivadas). O tracking é lido sob
demanda por jogada (não é ingerido). A API também constrói a camada na
inicialização e expõe as contagens em `GET /api/stats`.

## Status atual

- **Fase 0 (fundação):** monorepo, CORS, `/api/health`, tela inicial do frontend. ✓
- **Fase 1 (camada de dados F1):** ingestão + normalização em DuckDB, tabelas
  derivadas, leitor de tracking por jogada, `/api/stats`, testes de sanidade. ✓
- **Fase 2 (métricas base + F3 + F7):** endpoints de jogadores e rankings. ✓

### Endpoints (Fase 2)

- `GET /api/players?search=&limit=&offset=` — busca/listagem de jogadores.
- `GET /api/players/{nflId}` — ficha consolidada (painel de rusher e/ou blocador
  conforme o papel; splits por alinhamento e cobertura; uso por tipo de bloqueio).
- `GET /api/rankings?metric=&min_snaps=&limit=` — leaderboards por métrica com
  snap threshold. `GET /api/rankings/metrics` lista as métricas disponíveis.

> Nota: o frontend (F2/dashboard e telas) fica fora deste repositório por decisão
> de escopo — aqui é backend + dados.

Próxima etapa: **Fase 3 — filtros contextuais globais (F8)** aplicados aos
endpoints (ver [plano de implementação](features/plano_implementacao.md)).
