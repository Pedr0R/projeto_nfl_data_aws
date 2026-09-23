# Features Estruturais — Plataforma de Análise de Scout NFL

> Detalhamento das features estruturais (base) da solução. Estas são a fundação
> sobre a qual os diferenciais competitivos serão construídos. Dataset: NFL Big
> Data Bowl 2023 (pass rush x pass protection), temporada 2021, semanas 1-8.

## Índice

1. [Visão geral e arquitetura de dados](#1-visão-geral-e-arquitetura-de-dados)
2. [F1 — Pipeline de ingestão e camada de dados](#f1--pipeline-de-ingestão-e-camada-de-dados)
3. [F2 — Dashboard principal (visão geral)](#f2--dashboard-principal-visão-geral)
4. [F3 — Ficha de scout do jogador (player profile)](#f3--ficha-de-scout-do-jogador-player-profile)
5. [F4 — Comparação de jogadores](#f4--comparação-de-jogadores)
6. [F5 — Explorador de jogadas (play explorer)](#f5--explorador-de-jogadas-play-explorer)
7. [F6 — Visualização animada de jogada](#f6--visualização-animada-de-jogada)
8. [F7 — Ranking e leaderboards](#f7--ranking-e-leaderboards)
9. [F8 — Filtros contextuais globais](#f8--filtros-contextuais-globais)
10. [Métricas base (dicionário)](#métricas-base-dicionário)
11. [Ganchos para os diferenciais](#ganchos-para-os-diferenciais)
12. [Stack e priorização](#stack-e-priorização)

---

## 1. Visão geral e arquitetura de dados

A solução é organizada em camadas. As features estruturais (F1-F8) entregam o
"esperado" de uma ferramenta de scout; os diferenciais (ver seção final) plugam
em cima dessa base.

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (React + TypeScript)                           │
│  F2 Dashboard · F3 Ficha · F4 Comparação · F5 Explorer   │
│  F6 Animação · F7 Rankings · F8 Filtros                  │
├─────────────────────────────────────────────────────────┤
│  API REST (FastAPI)                                      │
│  endpoints por jogador / jogada / matchup / ranking      │
│  serialização (Pydantic) · filtros contextuais (F8)      │
├─────────────────────────────────────────────────────────┤
│  Camada de métricas (feature store)                      │
│  métricas por jogador / jogada / matchup                 │
├─────────────────────────────────────────────────────────┤
│  Camada de dados normalizada (F1)                        │
│  joins: games · plays · players · pff · tracking         │
└─────────────────────────────────────────────────────────┘
```

O backend (FastAPI) expõe a camada de métricas via API REST; o frontend (React)
consome esses endpoints. A comunicação é sempre por JSON, com os filtros globais
(F8) trafegando como query params / corpo de request compartilhado.

### Modelo relacional (chaves de join)

| De | Para | Chave |
|----|------|-------|
| `plays` | `games` | `gameId` |
| `plays` | `pffScoutingData` | `gameId` + `playId` |
| `pffScoutingData` | `players` | `nflId` |
| `pffScoutingData` | `tracking` | `gameId` + `playId` + `nflId` |
| `pff.pff_nflIdBlockedPlayer` | `players` | `nflId` (matchup bloqueador→rusher) |

Volume de referência: ~8,5k jogadas, ~188k linhas de scout PFF, ~1,7k jogadores,
122 arquivos de tracking (~11M linhas totais a 10 fps).

---

## F1 — Pipeline de ingestão e camada de dados

**Objetivo:** transformar os 5 CSVs brutos numa camada consultável e reutilizável
por todas as features.

### Requisitos funcionais
- Carregar `games`, `plays`, `players`, `pffScoutingData` em memória/banco leve.
- Carregar tracking sob demanda por `gameId` (arquivo é grande; não carregar tudo).
- Normalizar tipos: `NA` → null, `gameClock` → segundos, `height` "6-4" → polegadas.
- Normalizar direção da jogada: espelhar coordenadas quando `playDirection = left`
  para que toda análise assuma o ataque indo para a direita (padroniza x/y/dir/o).
- Materializar tabelas derivadas ("feature store"):
  - `player_play` — uma linha por jogador/jogada com flags PFF + contexto.
  - `player_season` — agregados por jogador na amostra.
  - `matchup` — uma linha por par bloqueador↔rusher por jogada.
- Cache dos agregados para não recomputar a cada request.

### Requisitos não-funcionais
- Ingestão idempotente (rodar de novo não duplica).
- Tempo de carga inicial aceitável para demo (< ~30s para agregados sem tracking).
- Validação de schema (colunas esperadas presentes) com erro claro.

### Entradas → saídas
- Entrada: `data/*.csv`.
- Saída: tabelas normalizadas (Parquet/DuckDB/SQLite) + agregados em cache.
- Consumo: a camada de dados é acessada pelo backend FastAPI, que serve os
  agregados às telas via endpoints REST (nenhum CSV é lido diretamente no front).

---

## F2 — Dashboard principal (visão geral)

**Objetivo:** tela de entrada com o "estado do mundo" e navegação para o resto.

### Componentes
- **KPIs de topo:** nº de jogos, jogadas de passe, jogadores na amostra, sacks,
  taxa média de pressão da amostra.
- **Leaderboards resumidos:** top pass rushers (pressão) e top bloqueadores
  (proteção), com atalho para a ficha completa (F3).
- **Distribuições:** pressão por tipo de cobertura (`pff_passCoverage`), por
  formação ofensiva (`offenseFormation`), por down/distância.
- **Navegação:** busca de jogador, atalhos para comparação (F4) e explorer (F5).

### Interações
- Todo widget respeita os filtros globais (F8).
- Clicar num jogador → abre F3. Clicar numa jogada → abre F5/F6.

---

## F3 — Ficha de scout do jogador (player profile)

**Objetivo:** consolidar tudo sobre um jogador num só lugar. Adapta-se ao papel.

### Cabeçalho
- Nome, posição oficial, altura/peso, faculdade, nº de snaps na amostra.

### Painel para PASS RUSHERS (defesa)
- **Produção:** hits, hurries, sacks (totais e por snap).
- **Pressão total** = (hits + hurries + sacks) / snaps de rush.
- **Win rate** contra bloqueio (derrotou o bloqueador).
- Split por `pff_positionLinedUp` (onde alinhou) e por tipo de cobertura atrás.
- **Tendência por down/distância** e por formação adversária.

### Painel para BLOCADORES (ataque)
- **Pressão permitida:** hits/hurries/sacks allowed (totais e por snap).
- **Beaten rate** (`pff_beatenByDefender`).
- **Eficiência por tipo de bloqueio** (`pff_blockType`: PP, PA, SW, etc.).
- **Backfield block rate** (`pff_backFieldBlock`).

### Painel para QB / rota (quando aplicável)
- QB: perfil de resultado do passe (`passResult`), dropback type, play action.
- Rota: presença por formação; base para métricas de separação (diferencial).

### Rodapé
- Lista das jogadas do jogador → link para F5/F6.

---

## F4 — Comparação de jogadores

**Objetivo:** colocar 2 a 4 jogadores lado a lado de forma justa.

### Requisitos funcionais
- Seleção de 2-4 jogadores (idealmente do mesmo grupo posicional).
- **Tabela comparativa** das métricas base normalizadas por snap.
- **Radar/spider chart** das dimensões-chave (pressão, win rate, consistência,
  produção em situações de passe puro).
- **Barras lado a lado** por métrica individual.
- **Normalização justa:** só comparar sobre snaps elegíveis (ex.: excluir jogadas
  em que o jogador não teve papel de rush/bloqueio); exibir tamanho de amostra.
- **Split contextual:** aplicar F8 para comparar "no mesmo cenário" (ex.: só em
  Cover-1, só em 3rd & long).

### Cuidados de design
- Sempre mostrar nº de snaps ao lado de cada métrica (evita conclusão com amostra
  pequena).
- Destacar visualmente o melhor valor por linha, mas sem esconder o contexto.

---

## F5 — Explorador de jogadas (play explorer)

**Objetivo:** encontrar e inspecionar jogadas específicas.

### Requisitos funcionais
- **Tabela filtrável** de jogadas: descrição, down, distância, formação,
  cobertura, resultado, pressão (sim/não), jogadores-chave.
- Filtros: por time, jogador envolvido, tipo de cobertura, resultado, presença de
  sack/hit/hurry, play action.
- **Busca textual** no `playDescription`.
- Ordenação por qualquer coluna.
- Linha clicável → detalhe da jogada:
  - Contexto completo (plays).
  - Lista de participantes com papel PFF e resultado individual.
  - Matchups reconstruídos (bloqueador → rusher via `pff_nflIdBlockedPlayer`).
  - Botão "ver animação" → F6.

---

## F6 — Visualização animada de jogada

**Objetivo:** reconstrução 2D frame a frame a partir do tracking.

### Requisitos funcionais
- Campo 2D em escala (120 x 53.3 jardas), com linha de scrimmage e marcadores.
- Posições de todos os 22 jogadores + bola por frame (`x`, `y`).
- Setas de **orientação** (`o`) e **direção do movimento** (`dir`).
- **Play controls:** play/pause, scrub por frame, velocidade.
- **Eventos marcados** na timeline (`ball_snap`, `pass_forward`, `pass_arrived`,
  `qb_sack`, etc.) para pular direto ao momento.
- Legenda por time/cor; distinção visual ataque vs. defesa.
- Coordenadas já normalizadas por `playDirection` (via F1).

### Requisitos não-funcionais
- Renderização fluida de uma jogada (dezenas a centenas de frames) no cliente
  React (canvas/SVG ou lib de visualização como D3/Canvas).
- Backend serve os frames da jogada aberta via endpoint dedicado; o front recebe
  só o tracking daquela jogada (não o arquivo inteiro) e anima localmente.

> Nota: animação básica é commodity no ecossistema Big Data Bowl. O valor vem de
> sobrepor as métricas dos diferenciais (ver seção final).

---

## F7 — Ranking e leaderboards

**Objetivo:** ordenar jogadores/unidades pelas métricas base.

### Requisitos funcionais
- Rankings de pass rushers e de blocadores por qualquer métrica base.
- **Snap threshold** configurável (mínimo de snaps para entrar no ranking).
- Rankings por unidade/time (agregado da linha ofensiva, do front defensivo).
- Aplicação dos filtros globais (F8) para rankings contextuais.
- Exportação da tabela (CSV) para uso do coach.

---

## F8 — Filtros contextuais globais

**Objetivo:** um painel de filtros compartilhado que redefine o escopo de TODAS as
features simultaneamente.

### Dimensões de filtro
- **Jogo/semana/time** (via `games` + `possessionTeam`/`defensiveTeam`).
- **Situação:** down, faixa de `yardsToGo`, quarter, faixa de `gameClock`,
  placar (à frente/atrás).
- **Esquema:** `offenseFormation`, `personnelO`, `personnelD`, `defendersInBox`,
  `dropBackType`, `pff_playAction`.
- **Cobertura:** `pff_passCoverage`, `pff_passCoverageType` (man/zone).
- **Resultado:** `passResult`, presença de sack/hit/hurry.

### Comportamento
- Estado de filtro persistente ao navegar entre F2-F7.
- Indicador visível de "amostra atual" (nº de jogadas/snaps após filtro).
- "Limpar filtros" e presets rápidos (ex.: "3rd & long", "red zone").

---

## Métricas base (dicionário)

Métricas comuns de mercado, usadas como fundação. Todas normalizáveis por snap.

| Métrica | Definição | Fonte |
|---------|-----------|-------|
| Pressões | hits + hurries + sacks | `pff_hit`, `pff_hurry`, `pff_sack` |
| Taxa de pressão | pressões / snaps de rush | PFF |
| Pressão permitida | hits/hurries/sacks allowed | `pff_*Allowed` |
| Beaten rate | jogadas beaten / snaps de bloqueio | `pff_beatenByDefender` |
| Win rate (rusher) | jogadas em que venceu o bloqueio / snaps | PFF + matchup |
| Snaps elegíveis | contagem por `pff_role` | `pff_role` |
| Uso por bloqueio | distribuição de `pff_blockType` | PFF |

> Estas métricas replicam o que PFF/ESPN já oferecem. Servem de baseline e de
> âncora de credibilidade — NÃO são o diferencial.

---

## Ganchos para os diferenciais

Cada feature estrutural foi desenhada para receber os diferenciais sem retrabalho:

| Diferencial (roadmap) | Onde se pluga na base |
|-----------------------|-----------------------|
| **Blame assignment** (culpa objetiva pela pressão) | F5 detalhe da jogada + F6 (destacar blocador culpado) + coluna em F3 |
| **Detecção de stunts/twists** | F5 (flag na jogada) + F6 (trajetórias cruzadas) + métrica de pickup em F4 |
| **Pocket displacement / ghost defender** | F6 (contorno do pocket) + métrica em F3 |
| **Fit esquemático** | F8 (filtros) + F4 (comparação contextual) |
| **Processamento pós-snap do QB** | F5/F6 (timeline de eventos vs. estado do pocket) |
| **Tell pré-snap / tendência** | F5 (frames pré-snap) + alerta no F2 |

O `pff_nflIdBlockedPlayer` (link explícito de matchup) + tracking normalizado (F1)
são a base técnica que habilita a maioria dos diferenciais e que raramente aparece
combinada em ferramentas públicas.

---

## Stack e priorização

### Stack sugerida
- **Dados (camada F1):** Python + pandas + DuckDB (ou Parquet) para ingestão,
  normalização e feature store.
- **Backend / API:** FastAPI (Python) expondo a camada de métricas via REST,
  com Pydantic para os schemas de resposta e Uvicorn como servidor ASGI.
- **Frontend / UI:** React + TypeScript (cobre F2-F8), consumindo a API por
  `fetch`/axios; gráficos com uma lib de charting (ex.: Recharts/Visx/D3).
- **Animação (F6):** renderização 2D no cliente React via Canvas ou SVG (D3),
  animando frame a frame o tracking servido pelo endpoint da jogada.

O backend e o frontend são projetos separados (ex.: `backend/` e `frontend/`),
comunicando-se por JSON. Isso mantém a camada de dados desacoplada da UI e
permite evoluir cada lado independentemente.

### Ordem de implementação (MVP → diferencial)
1. **F1** (bloqueia todo o resto) — obrigatório primeiro.
2. **F3 + F7** (ficha + ranking) — valor imediato com métricas base.
3. **F8** (filtros) — multiplica o valor de tudo que já existe.
4. **F2** (dashboard) — costura a navegação.
5. **F5 + F6** (explorer + animação) — vitrine visual.
6. **F4** (comparação) — reforço analítico.
7. **Diferenciais** — construídos sobre F5/F6/F3 já prontos.

> Regra de escopo p/ hackathon: base sólida o suficiente para dar credibilidade,
> mas o tempo de destaque vai para 1-2 diferenciais bem executados.
