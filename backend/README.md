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
├── main.py       # instancia FastAPI, CORS, registra routers
├── core/         # config (pydantic-settings)
├── api/          # routers por domínio (health e, nas próximas fases, players/plays/…)
├── schemas/      # modelos Pydantic (contrato de resposta)
├── data/         # (Fase 1) ingestão, normalização, conexão DuckDB
├── features/     # (Fase 1+) cálculo de métricas / feature store
└── services/     # (Fase 2+) regras de negócio entre data e api
tests/            # testes de contrato e de métricas
```

## Configuração

Variáveis de ambiente com prefixo `NFL_` (ver `.env.example`). Ex.: `NFL_DATA_DIR`
para apontar aos CSVs do dataset.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
