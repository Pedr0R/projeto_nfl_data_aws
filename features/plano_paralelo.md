# Plano de Execução Paralela — Backend x Frontend

> Reestruturação do `plano_implementacao.md` em **duas trilhas independentes**
> (Backend e Frontend) que dois agentes podem tocar **simultaneamente sem
> colidir**. A fronteira entre elas é o **contrato de API** (OpenAPI): o back
> produz, o front consome. Enquanto o contrato de um endpoint estiver acordado,
> os dois lados avançam em paralelo.

## Como ler este documento

- **Trilha B (Backend)** e **Trilha F (Frontend)** listam tarefas na ordem de
  execução de cada agente.
- Cada tarefa tem **arquivos donos** (quem pode editar) para evitar dois agentes
  no mesmo arquivo.
- **Pontos de sincronização (SYNC)** marcam onde uma trilha precisa que a outra
  tenha publicado algo (normalmente um contrato de endpoint).
- O front nunca fica bloqueado esperando o back: usa **mocks tipados** derivados
  do contrato até o endpoint real existir.

---

## 1. Regra de ouro: como evitar colisão entre agentes

1. **Nenhum arquivo tem dois donos.** Um arquivo pertence a UMA trilha por vez.
   Ver a tabela de propriedade abaixo.
2. **O contrato vem antes do código.** Ao criar um endpoint, o agente de backend
   primeiro fixa o formato de request/response (schema Pydantic) e anota aqui na
   seção "Contrato". Só então o front pode gerar o tipo e mockar.
3. **`main.py` é ponto sensível.** Só o agente de backend edita. Novos routers
   são registrados por ele. Nunca importe um router antes do arquivo existir
   (foi exatamente o que quebrou o boot na Fase 2).
4. **Tipos TS gerados do OpenAPI são a ponte.** O front regenera
   `frontend/src/api/types.ts` a partir de `/openapi.json` quando o back publica
   um endpoint. Entre uma geração e outra, o front usa mock.
5. **Commits pequenos e por trilha.** Facilita reverter sem atropelar a outra
   trilha.

### Tabela de propriedade de arquivos/pastas

| Caminho | Dono | Observação |
|---------|------|------------|
| `backend/app/main.py` | Backend | registro de routers, CORS, lifespan |
| `backend/app/api/**` | Backend | routers |
| `backend/app/services/**` | Backend | regras de negócio |
| `backend/app/schemas/**` | Backend | contrato Pydantic (fonte da verdade) |
| `backend/app/features/**` | Backend | cálculo de métricas |
| `backend/app/data/**` | Backend | camada F1 (já pronta; congelada) |
| `backend/tests/**` | Backend | testes de API/métricas |
| `frontend/src/api/**` | Frontend | client HTTP + tipos gerados/mocks |
| `frontend/src/components/**` | Frontend | componentes reutilizáveis |
| `frontend/src/features/**` | Frontend | telas F2-F8 |
| `frontend/src/hooks/**` | Frontend | data fetching + estado de filtros |
| `frontend/src/lib/**` | Frontend | utils |
| `frontend/src/App.tsx`, `main.tsx`, rotas | Frontend | shell da SPA |
| `features/**` (docs) | Compartilhado | editar só a própria seção |

> **Zona neutra / cuidado:** `README.md` e os arquivos em `features/` são
> compartilhados. Combine edições por seção para não sobrescrever.

---

## 2. Contrato de API (fronteira entre as trilhas)

Fonte única: os schemas Pydantic no backend geram o `/openapi.json`. Esta tabela
é o "handshake" — o back marca ✅ quando o endpoint está publicado e estável; a
partir daí o front troca o mock pelo tipo real.

| Endpoint | Feature | Fase | Status contrato |
|----------|---------|------|-----------------|
| `GET /api/health` | infra | 0 | ✅ publicado |
| `GET /api/stats` | infra | 1 | ✅ publicado |
| `GET /api/players` | F3 | 2 | 🔄 em andamento (outro agente) |
| `GET /api/players/{nflId}` | F3 | 2 | 🔄 em andamento |
| `GET /api/rankings` | F7 | 2 | 🔄 em andamento |
| `GET /api/rankings/metrics` | F7 | 2 | 🔄 em andamento |
| `GET /api/filters/options` | F8 | 3 | ⬜ a definir (Trilha B) |
| filtros F8 como query params transversais | F8 | 3 | ⬜ a definir (Trilha B) |
| `GET /api/overview` | F2 | 4 | ⬜ a definir |
| `GET /api/plays` | F5 | 5 | ⬜ a definir |
| `GET /api/plays/{gameId}/{playId}` | F5 | 5 | ⬜ a definir |
| `GET /api/plays/{gameId}/{playId}/tracking` | F6 | 5 | ⬜ a definir |
| `GET /api/compare` | F4 | 6 | ⬜ a definir |

### Filtros globais F8 (query params comuns a vários endpoints)

Subconjunto de alto impacto para o MVP (o restante é incremental):

`week`, `team`, `down`, `yards_to_go_min`, `yards_to_go_max`, `quarter`,
`offense_formation`, `dropback_type`, `play_action`, `pass_coverage`,
`pass_coverage_type`, `pass_result`, `pressure`, `min_snaps`.

> Regra: qualquer endpoint que aceite F8 usa os **mesmos nomes** de query param.
> O back centraliza isso num dependency reutilizável (`FilterParams`) para o
> contrato ficar idêntico em todo lugar.

---

## 3. Trilha B — Backend (Agente Backend)

> Pré-requisito: **encerrar a Fase 2** (criar o `api/players.py` que falta e
> destravar o boot). Só então seguir para F8.

### B0 — Estabilizar Fase 2 (desbloqueio)
- Criar `backend/app/api/players.py` (router `/players` e `/players/{nflId}`)
  consumindo `services/players.py` (já existe).
- Confirmar que `main.py` sobe sem `ImportError` e `/docs` lista os endpoints.
- Teste de contrato mínimo para `/players` e `/rankings`.
- **Arquivos:** `api/players.py`, `main.py`, `tests/`.
- **SYNC → Front:** marca `GET /api/players*` e `/rankings*` como ✅ publicado.

### B1 — F8: dependency de filtros reutilizável
- `services/filters.py`: `FilterParams` (dataclass/Pydantic) + função que gera
  cláusula `WHERE` parametrizada sobre `player_play` (evita SQL injection: usar
  placeholders `?`).
- Aplicar em `list_players`, `get_ranking` e nos splits da ficha.
- **Arquivos:** `services/filters.py`, `services/players.py`, `api/players.py`,
  `api/rankings.py`.

### B2 — F8: endpoint de opções
- `GET /api/filters/options` → valores distintos possíveis por dimensão
  (weeks, teams, downs, coverages, formations…) para popular os controles.
- Schema `schemas/filters.py`.
- **Arquivos:** `api/filters.py`, `services/filters.py`, `schemas/filters.py`,
  `main.py` (registrar router).
- **SYNC → Front:** marca `GET /api/filters/options` e os query params F8 como ✅.

### B3 — F2: overview (depois de F8)
- `GET /api/overview` (KPIs + distribuições enxutas), respeitando F8.
- **Arquivos:** `api/overview.py`, `services/overview.py`, `schemas/overview.py`,
  `main.py`.
- **SYNC → Front:** marca `GET /api/overview` ✅.

### B4 — F5: plays + detalhe (essencial) / F6 tracking (se sobrar tempo)
- `GET /api/plays`, `GET /api/plays/{gameId}/{playId}` (+ participantes e
  matchups via `matchup`). `.../tracking` só se F6 entrar.
- **Arquivos:** `api/plays.py`, `services/plays.py`, `schemas/plays.py`, `main.py`.
- **SYNC → Front:** marca endpoints de plays ✅.

### B5 — diferencial (blame assignment) + F4 compare (opcional)
- Coluna de "culpa pela pressão" no detalhe da jogada (usa `matchup`).
- `GET /api/compare` só se houver tempo.

---

## 4. Trilha F — Frontend (Agente Frontend)

> O front **não espera** o back. Cada tela é construída contra um **mock tipado**
> derivado do contrato; ao endpoint publicar (✅), troca o mock pela chamada real.
> Nenhuma tarefa abaixo toca arquivos da Trilha B.

### F0 — Fundação da SPA (sem depender do back)
- Instalar/configurar **react-router**, **@tanstack/react-query** e uma lib de
  charts (Recharts). Provider do Query + Router em `main.tsx`/`App.tsx`.
- `lib/format.ts` (percentuais, por-snap), `lib/teams.ts` (cores/siglas).
- Layout base: header + navegação entre telas (rotas vazias por enquanto).
- **Arquivos:** `frontend/src/**` (App, main, lib, components/layout).

### F1 — Camada de API do front + mocks tipados
- `api/types.ts`: tipos gerados do `/openapi.json` para o que já está ✅
  (health, stats) e **tipos manuais espelhando o contrato** para o que ainda é
  🔄/⬜ (players, rankings, filters…).
- `api/mocks/`: fixtures que respeitam os tipos, para desenvolver telas offline.
- Flag simples (`USE_MOCK`) por endpoint para alternar mock ↔ real.
- **Arquivos:** `frontend/src/api/**`.

### F2 — Tela de Rankings (F7) [contrato já em andamento]
- Tabela de leaderboard: seletor de métrica, `min_snaps`, ordenação, nº de snaps
  sempre visível. Consome `/api/rankings` (mock até B0 publicar).
- **Arquivos:** `features/rankings/**`, `components/DataTable/**`, `hooks/`.
- **SYNC ← Back B0:** ao publicar `/rankings`, remover mock.

### F3 — Tela de Ficha do jogador (F3)
- Busca de jogador (`/api/players`) + ficha (`/api/players/{id}`) com painéis
  condicionais (rusher/blocador), splits e métricas por snap.
- **Arquivos:** `features/player/**`, `components/**`, `hooks/`.
- **SYNC ← Back B0.**

### F4 — Painel de Filtros Globais (F8)
- Contexto de filtros + sincronização com URL search params; injeta os params F8
  em toda request; indicador de "amostra atual"; botão limpar.
- Popular controles com `/api/filters/options` (mock até B2).
- **Arquivos:** `features/filters/**`, `hooks/useFilters.ts`, `api/**`.
- **SYNC ← Back B1/B2.**

### F5 — Dashboard (F2)
- KPIs + leaderboards resumidos (reusa componentes de F2/rankings) + busca.
  Consome `/api/overview` (mock até B3).
- **Arquivos:** `features/dashboard/**`.
- **SYNC ← Back B3.**

### F6 — Explorer (F5) e, se houver tempo, Animação (F6)
- Tabela de jogadas filtrável + detalhe com participantes/matchups.
- Campo 2D animado só se F6 entrar no escopo.
- **Arquivos:** `features/plays/**`, `components/Field2D/**`.
- **SYNC ← Back B4.**

---

## 5. Linha do tempo paralela (visão de fases)

```
Tempo →
Back:  [B0 fecha Fase2]→[B1 F8 filtros]→[B2 options]→[B3 overview]→[B4 plays]→[B5 diferencial]
Front: [F0 fundação ]→[F1 api+mocks ]→[F2 rankings]→[F3 ficha ]→[F4 filtros]→[F5 dash]→[F6 explorer]
                          ▲ mocks deixam o front andar sem esperar o back
SYNC:              B0✅ destrava F2/F3 reais · B2✅ destrava F4 real · B3✅ destrava F5 · B4✅ destrava F6
```

Ambas as trilhas começam imediatamente. O único gargalo real é **B0** (fechar a
Fase 2), e mesmo assim o front avança em F0/F1 e monta as telas com mock antes
disso.

---

## 6. Definição de pronto por trilha

**Backend:** endpoint no OpenAPI + schema Pydantic + respeita F8 quando aplicável
+ teste de contrato/métrica + sobe local com o comando do README.

**Frontend:** tela consome o tipo do contrato (mock ou real), trata
loading/empty/error, respeita filtros globais (F8) e navega pelas rotas.

**Integração (fim de cada SYNC):** trocar mock pela chamada real e validar no
`/docs` + na tela que o formato bate. Se divergir, o **contrato (schema
Pydantic) é a fonte da verdade** e o front se ajusta.
