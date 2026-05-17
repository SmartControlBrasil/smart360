# AI Digital Twin Operacional

## Visao Geral
O Digital Twin Operacional do SMART360 representa em tempo quase real o estado consolidado de unidades e ativos. Ele combina dados operacionais, sinais de IA, eventos do barramento, historico recente e perfil de risco em um contexto unico para War Room, copilotos, agentes, simulacoes e decisao.

## Tipos iniciais
- `site_operational_twin`
- `asset_operational_twin`

## Fluxo
1. Eventos de dominio relevantes entram pelo `integration_bus`.
2. O subscriber `twin_projection_refresh` chama o `DigitalTwinOrchestrator`.
3. O orquestrador resolve o twin da unidade e/ou do ativo.
4. Projectors dedicados calculam estado, risco, timeline, sinais e resumo.
5. O twin persistido atualiza projections, signals e snapshots.
6. O contexto resultante fica disponivel na API, no shell e no War Room.

## Projectors implementados
- `SiteOperationalTwinProjector`
- `AssetOperationalTwinProjector`
- `TwinTimelineProjector`

## Sinais cobertos
- backlog operacional
- preventiva vencida
- falha critica recente
- checklist NOK
- recomendacao relevante de agente

## Integracoes
- `Real-Time Event Bus`: recalculo reativo por evento
- `Executive War Room`: hotspot de twins em atencao
- `Manager Copilot`: cards recentes de twins no contexto
- `Simulation Engine`: base pronta para uso do twin como baseline contextual
- `Auto-Optimization Loop`: snapshots e risco ficam disponiveis para comparacao temporal

## Endpoints
- `GET /api/v1/ai-digital-twins/twins/`
- `GET /api/v1/ai-digital-twins/twins/{public_id}/`
- `GET /api/v1/ai-digital-twins/twins/by-site/{site_public_id}/`
- `GET /api/v1/ai-digital-twins/twins/by-asset/{asset_public_id}/`
- `GET /api/v1/ai-digital-twins/twins/{public_id}/summary/`
- `GET /api/v1/ai-digital-twins/twins/{public_id}/timeline/`
- `GET /api/v1/ai-digital-twins/twins/{public_id}/active-signals/`
- `GET /api/v1/ai-digital-twins/twins/{public_id}/risk-profile/`
- `GET /api/v1/ai-digital-twins/twins/{public_id}/snapshots/`

## Shell
- `GET /app/ai-agents/digital-twins/`

## Regras heuristicas atuais
- risco da unidade considera backlog, falhas criticas, preventivas vencidas, flags de atencao e anomalias
- risco do ativo considera criticidade, falhas recentes, preventivas vencidas, checklist NOK, atrasos e sinais do Maintenance Agent
- timeline usa service orders, falhas, historico do ativo e recomendacoes recentes

## Limitacoes atuais
- ainda nao existe twin de contrato, portfolio ou regiao
- a projeção ainda usa heuristica deterministica e janelas fixas
- streaming forte do twin ainda depende do refresh via bus + shell, nao de tela dedicada websocket

## Proximos passos recomendados
- twin por contrato e cliente
- baseline nativo do twin no Simulation Engine
- comparacao temporal mais rica entre snapshots
- contexto universal do twin para copilotos e agentes
