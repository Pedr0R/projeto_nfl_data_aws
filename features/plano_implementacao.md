# Plano de Implementação — Plataforma de Análise de Scout NFL

> Tradução do design (ver `features_gerais.md`) em fases executáveis. Stack:
> **FastAPI** (backend) + **React + TypeScript** (frontend), com camada de dados
> em **Python + pandas + DuckDB**. Dataset: NFL Big Data Bowl 2023, temporada
> 2021, semanas 1-8.

## Índice

1. [Estrutura do repositório](#1-estrutura-do-repositório)
2. [Arquitetura técnica](#2-arquitetura-técnica)
3. [Contrato de API (visão geral)](#3-contrato-de-api-visão-geral)
4. [Fases de implementação](#4-fases-de-implementação)
5. [Backlog por feature](#5-backlog-por-feature)
6. [Ordem de dependências](#6-ordem-de-dependências)
7. [Riscos e mitigação](#7-riscos-e-mitigação)
8. [Definição de pronto (DoD)](#8-definição-de-pronto-dod)

---

## 1. Estrutura do repositório

Monorepo com backend e frontend separados, dados fora do versionamento.

```
projeto_nfl_data_aws/
├── backend/
│   ├── app/
│   │   ├── main.py               # instancia FastAPI + rotas + CORS
│   │   ├── api/                  # routers por domínio (players, plays, rankings…)
│   │   ├── core/                 # config, settings, dependências
│   │   ├── data/                 # camada F1: ingestão, normalização, conexão DuckDB
│   │   ├── features/             # feature store: cálculo de métricas/agregados
│   │   ├── schemas/              # modelos Pydantic (contrato de resposta)
│   │   └── services/             # regras de negócio entre data e api
│   ├── tests/
│   ├── pyproject.toml            # deps: fastapi, uvicorn, pandas, duckdb, pydantic
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── api/                  # client HTTP + tipos gerados do contrato
│   │   ├── components/           # componentes reutilizáveis (charts, tabelas, campo 2D)
│   │   ├── features/             # telas F2-F8 (dashboard, ficha, comparação…)
│   │   ├── hooks/                # data fetching, estado de filtros globais (F8)
│   │   ├── lib/                  # utils (formatação, cores de time)
│   │   └── App.tsx
│   ├── package.json              # react, typescript, react-router, tanstack-query, recharts
│   └── vite.config.ts
├── data/                         # symlink/cópia dos CSVs (NÃO versionar)
├── .gitignore
└── features/                     # documentação (features_gerais.md, este plano)
```

---

## 2. Arquitetura técnica

### Backend (FastAPI)
- **Camada de dados (F1):** na inicialização, carrega os CSVs pequenos
  (`games`, `plays`, `players`, `pffScoutingData`) num DuckDB (arquivo `.duckdb`
  ou em memória). Tracking permanece em disco e é lido sob demanda por `gameId`.
- **Feature store:** views/tabelas materializadas em DuckDB (`player_play`,
  `player_season`, `matchup`) computadas uma vez e cacheadas.
- **API:** routers finos → chamam `services` → consultam DuckDB → serializam via
  Pydantic. Filtros globais (F8) entram como query params reutilizáveis.
- **Cache:** agregados em cache de processo (`functools.lru_cache` ou tabela
  materializada); tracking de jogada com cache leve por `(gameId, playId)`.

### Frontend (React + TypeScript)
- **Data fetching:** TanStack Query (cache, revalidação, estados de loading).
- **Estado global de filtros (F8):** contexto/URL search params compartilhados
  entre todas as telas; toda request injeta os filtros ativos.
- **Roteamento:** React Router — rotas para dashboard, ficha, comparação,
  explorer, animação, rankings.
- **Charts:** Recharts para gráficos padrão; Canvas/SVG (ou D3) para o campo 2D
  animado (F6).

### Contrato compartilhado
- OpenAPI gerado automaticamente pelo FastAPI (`/docs`, `/openapi.json`).
- Tipos TypeScript do front gerados a partir do `openapi.json` (ex.:
  `openapi-typescript`) para manter front e back em sincronia.

---

## 3. Contrato de API (visão geral)

Endpoints principais (todos aceitam os filtros globais F8 como query params).

| Método | Rota | Descrição | Feature |
|--------|------|-----------|---------|
| GET | `/api/health` | healthcheck | infra |
| GET | `/api/overview` | KPIs de topo + distribuições | F2 |
| GET | `/api/players` | busca/listagem de jogadores | F2/F3 |
| GET | `/api/players/{nflId}` | ficha consolidada (adaptada ao papel) | F3 |
| GET | `/api/players/{nflId}/plays` | jogadas do jogador | F3→F5 |
| GET | `/api/compare?ids=...` | métricas de 2-4 jogadores lado a lado | F4 |
| GET | `/api/plays` | tabela filtrável de jogadas | F5 |
| GET | `/api/plays/{gameId}/{playId}` | detalhe + participantes + matchups | F5 |
| GET | `/api/plays/{gameId}/{playId}/tracking` | frames da jogada (animação) | F6 |
| GET | `/api/rankings` | leaderboards por métrica + snap threshold | F7 |
| GET | `/api/filters/options` | valores possíveis dos filtros (F8) | F8 |

> Filtros F8 (query params comuns): `week`, `team`, `down`, `yardsToGoMin/Max`,
> `quarter`, `offenseFormation`, `personnelO/D`, `dropBackType`, `playAction`,
> `passCoverage`, `passCoverageType`, `passResult`, `pressure`, `minSnaps`.

---

## 4. Fases de implementação

Cada fase é entregável e demonstrável. Ordem respeita dependências (F1 primeiro).

### Fase 0 — Fundação (setup)
- Scaffold `backend/` (FastAPI + Uvicorn) e `frontend/` (Vite + React + TS).
- `.gitignore` (ignora `data/`, `.duckdb`, `node_modules`, `__pycache__`, `.venv`).
- CORS liberado para o dev do front; endpoint `/api/health`.
- README de setup (como rodar back e front localmente).
- **Entregável:** front consegue chamar `/api/health` e exibir "ok".

### Fase 1 — Camada de dados (F1) [bloqueia tudo]
- Loader dos 4 CSVs pequenos para DuckDB, com validação de schema.
- Normalização: `NA`→null, `gameClock`→segundos, `height` "6-4"→polegadas,
  espelhamento de coordenadas quando `playDirection = left`.
- Leitor de tracking sob demanda por `gameId`.
- Tabelas derivadas: `player_play`, `player_season`, `matchup`.
- Testes de sanidade (contagens de referência: ~8,5k jogadas, ~1,7k jogadores).
- **Entregável:** funções/consultas que retornam agregados corretos (sem API).

### Fase 2 — Métricas base + API de ficha e ranking (F3 + F7)
- Implementar dicionário de métricas (pressões, taxa de pressão, pressão
  permitida, beaten rate, win rate, snaps elegíveis, uso por bloqueio).
- Endpoints `/api/players/{nflId}`, `/api/players`, `/api/rankings`.
- Schemas Pydantic + testes de contrato.
- Frontend: tela de ficha (F3) e tela de rankings (F7) consumindo a API.
- **Entregável:** buscar jogador → ver ficha; ver leaderboards ordenáveis.

### Fase 3 — Filtros contextuais globais (F8)
- Query params de filtro aplicados de forma transversal nos services.
- Endpoint `/api/filters/options` para popular os controles.
- Frontend: painel de filtros global (contexto + URL), indicador de amostra
  atual, presets ("3rd & long", "red zone"), "limpar filtros".
- **Entregável:** mudar filtros redefine ficha e rankings simultaneamente.

### Fase 4 — Dashboard (F2)
- Endpoint `/api/overview` (KPIs + distribuições por cobertura/formação/down).
- Frontend: tela inicial com KPIs, leaderboards resumidos, distribuições,
  busca e navegação para F3/F5.
- **Entregável:** landing page navegável que costura o resto.

### Fase 5 — Explorer + Animação (F5 + F6)
- Endpoints `/api/plays`, `/api/plays/{gameId}/{playId}` (+ participantes e
  matchups via `pff_nflIdBlockedPlayer`) e `.../tracking`.
- Frontend F5: tabela filtrável/paginada, busca textual em `playDescription`,
  detalhe da jogada.
- Frontend F6: campo 2D em escala, 22 jogadores + bola por frame, setas de
  orientação/direção, play/pause/scrub, eventos na timeline.
- **Entregável:** achar jogada → ver detalhe → assistir animação.

### Fase 6 — Comparação (F4)
- Endpoint `/api/compare?ids=...` com normalização justa por snap + tamanho de
  amostra e suporte a split contextual (F8).
- Frontend: tabela comparativa, radar chart, barras lado a lado; destaque do
  melhor valor por linha com nº de snaps sempre visível.
- **Entregável:** 2-4 jogadores comparados de forma justa.

### Fase 7 — Polimento + diferencial
- Exportação CSV dos rankings (F7).
- Escolher 1-2 diferenciais (ver `features_gerais.md`) para destaque na demo,
  ex.: blame assignment em F5/F6.
- Ajustes de performance, tratamento de erro/empty states, responsividade.

---

## 5. Backlog por feature

| Feature | Backend | Frontend | Depende de |
|---------|---------|----------|------------|
| F1 | loaders, normalização, tabelas derivadas, cache | — | — |
| F3 | métricas + `/players/{id}` | tela de ficha por papel | F1 |
| F7 | `/rankings` + threshold | leaderboards ordenáveis + export | F1 |
| F8 | filtros transversais + `/filters/options` | painel global + presets | F1 |
| F2 | `/overview` | dashboard + navegação | F1, F3, F7, F8 |
| F5 | `/plays`, `/plays/{...}` + matchups | tabela + detalhe da jogada | F1, F8 |
| F6 | `/plays/{...}/tracking` | campo 2D animado | F1, F5 |
| F4 | `/compare` | tabela + radar + barras | F1, F3, F8 |

---

## 6. Ordem de dependências

```
Fase 0 (setup)
   └── Fase 1 · F1 (dados)            ← bloqueia tudo
          ├── Fase 2 · F3 + F7        ← valor imediato
          │      └── Fase 3 · F8      ← multiplica o valor
          │             └── Fase 4 · F2 (dashboard costura navegação)
          ├── Fase 5 · F5 → F6        ← vitrine visual (usa F8)
          └── Fase 6 · F4             ← usa F3 + F8
                 └── Fase 7 · diferencial + polimento
```

Regra de escopo p/ hackathon: garantir Fases 0-4 sólidas (credibilidade), e
investir o tempo de destaque em 1-2 diferenciais bem executados na Fase 7.

---

## 7. Riscos e mitigação

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Tracking pesado (~818 MB) trava a API | alto | nunca carregar tudo; ler só a jogada aberta; cache por jogada |
| Normalização de coordenadas errada (left/right) | alto | testar F6 visualmente cedo com jogadas conhecidas |
| Métricas incorretas minam credibilidade | alto | testes de sanidade em F1/F2 contra contagens de referência |
| Amostra pequena gera conclusões falsas | médio | expor nº de snaps sempre; snap threshold em rankings/comparação |
| Front e back fora de sincronia | médio | gerar tipos TS do `openapi.json`; contrato como fonte única |
| Escopo grande demais p/ hackathon | médio | priorizar Fases 0-4; diferencial só depois do MVP |

---

## 8. Definição de pronto (DoD)

Uma feature está pronta quando:
- Endpoint(s) documentado(s) no OpenAPI e com schema Pydantic.
- Tela consome a API real (sem mock), respeita filtros globais (F8) e trata
  loading/empty/error.
- Métricas conferidas contra números de referência quando aplicável.
- Testes mínimos: contrato da API e cálculo das métricas centrais.
- Roda localmente com o comando documentado no README.
