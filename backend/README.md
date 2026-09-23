# Backend — NFL Scout API (FastAPI)

API REST que serve as métricas de scout ao frontend. Ver o
[README raiz](../README.md) para o contexto do projeto.

## Setup

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/health

## Estrutura

```
app/
├── main.py       # instancia FastAPI, CORS, lifespan (build F1), registra routers
├── core/         # config (pydantic-settings)
├── api/          # routers por domínio (health, stats e, nas próximas fases, players/plays/…)
├── schemas/      # modelos Pydantic (contrato de resposta)
├── data/         # camada F1: DuckDB, normalização, tabelas derivadas, tracking
│   ├── database.py   # conexão + ingestão dos CSVs base (normalizados)
│   ├── normalize.py  # funções puras de normalização (gameClock, height, coords)
│   ├── derived.py    # player_play, matchup, player_season
│   ├── tracking.py   # leitura de tracking por jogada (sob demanda)
│   ├── schema.py     # colunas esperadas + constantes do campo
│   └── loader.py     # orquestra o build (idempotente); CLI: python -m app.data.loader
├── features/     # (Fase 2+) cálculo de métricas / feature store
└── services/     # (Fase 2+) regras de negócio entre data e api
tests/            # testes de contrato, normalização e sanidade da camada de dados
```

## Camada de dados (F1)

```powershell
# (re)construir a camada normalizada + derivada em DuckDB (idempotente)
.\.venv\Scripts\python.exe -m app.data.loader --stats
```

O DuckDB fica em `backend/.data/nfl_scout.duckdb` (não versionado). Os testes de
sanidade em `tests/test_data_layer.py` são pulados se o dataset não estiver
presente.

## Configuração

Variáveis de ambiente com prefixo `NFL_` (ver `.env.example`). Ex.: `NFL_DATA_DIR`
para apontar aos CSVs do dataset.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
