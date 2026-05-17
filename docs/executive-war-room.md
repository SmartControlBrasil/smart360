# Executive War Room

O `Executive War Room` e o centro de comando executivo do SMART360. Ele consolida operacao, IA, risco, agenda, marketplace, rentabilidade e governanca em uma unica experiencia de decisao.

## Arquitetura

Camadas principais:

- `apps/admin_shell/services/executive_war_room.py`
  agrega fontes operacionais, financeiras, IA e observabilidade
- `ExecutiveWarRoomView`
  renderiza a experiencia premium no shell
- `ExecutiveWarRoomDataView`
  expõe payload consolidado para refresh e integrações futuras

## Fontes de dados por painel

- `war_room_kpis`
  ordens de servico, decisoes pendentes, flags de agentes, agenda e marketplace
- `war_room_alerts`
  falhas, decisions awaiting approval, anomaly flags, profitability flags, marketplace gaps e critical asset attention
- `war_room_recommendations`
  `AgentRecommendation`
- `war_room_decisions`
  `AgentDecision`
- `war_room_simulations`
  `SimulationRun` + `SimulationResult`
- `war_room_operational_health`
  `ServiceOrder`, `FailureEvent`, `ScheduledVisit`, `TechnicianSchedule`
- `war_room_financial_health`
  `ExecutiveAnalyticsService` + profitability attention flags
- `war_room_marketplace_panel`
  `TechnicianServiceRequest`, `TechnicianAssignment`, `TechnicianMatchingRecord`
- `war_room_anomaly_panel`
  `AgentAnomalyAttentionFlag`
- `war_room_ai_governance`
  `AgentRun`, `OptimizationProposal`, `PolicyEvaluation`, `Experiment`
- `war_room_intelligence_feed`
  `SystemEventLog`

## Filtros globais

Filtros suportados:

- `period`
  `today`, `7d`, `30d`, `90d`
- `risk`
  vazio, `critical`, `high`, `medium`
- `domain`
  vazio, `maintenance`, `scheduling`, `profitability`, `marketplace`, `anomaly`

Os filtros afetam painéis, feed e filas executivas relevantes.

## Rotas

- tela principal:
  `/app/analytics/war-room/`
- payload resumido:
  `/app/analytics/war-room/data/`

## Integrações

- `AI Agents Center`
  recomendações, attention flags e agent runs
- `AI Decision Engine`
  fila de decisões pendentes com CTAs de aprovação/rejeição
- `Simulation Engine`
  simulações recentes para contexto de aprovação
- `Auto-Optimization Loop`
  propostas recentes de ajuste
- `Policy Studio`
  avaliações recentes de policy que impactam a operação
- `Experimentation Framework`
  experimentos ativos relevantes
- `Manager Copilot`
  entrada contextual para explicar o war room
- `AI Briefings`
  resumo do dia como abertura executiva
- `Observability`
  incidentes, jobs críticos e feed de eventos de alto valor

## Segurança e escopo

- respeita empresa/unidade ativa do shell
- cai para memberships quando não há empresa ativa
- usa permissões do shell (`dashboard:view`)
- CTAs de ação continuam protegidos por permissões específicas dos módulos de destino

## Limitações atuais

- foco principal em desktop/notebook
- feed executivo ainda usa regras curadas de evento, não classificação adaptativa
- filtros globais ainda são GET params simples, sem refresh parcial reativo
- parte da leitura financeira depende da disponibilidade de snapshots do `ExecutiveAnalyticsService`

## Próximos passos

- modo tempo real com polling/websocket
- wallboard mode
- war room por unidade/região
- visão comparativa entre tenants
- classificação adaptativa de alertas
- refresh parcial dos painéis via JSON endpoint
