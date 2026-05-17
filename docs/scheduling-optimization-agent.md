# Scheduling Optimization Agent

## Visao geral

O `Scheduling Optimization Agent` e a camada de inteligencia operacional de campo do `AI Agents Center`. Ele observa agenda, disponibilidade, rotas, visitas nao alocadas, SLA e assignments do marketplace para recomendar redistribuicao, encaixe, reordenacao e mitigacao de conflitos.

## Arquitetura

- `apps/ai_agents_center/agents/scheduling.py`
  - adaptador do agente especializado.
- `apps/ai_agents_center/services/scheduling_intelligence.py`
  - builder de contexto por tecnico, dia e site.
  - heuristicas deterministicas de agenda, rota e capacidade.
  - simulacoes de reordenacao e reatribuicao.
- `apps/ai_agents_center/services/scheduling_triggers.py`
  - centraliza disparos manuais, por evento e agendados.
- `apps/ai_agents_center/models.py`
  - `AgentScheduleHealthFlag` persiste a saude operacional da agenda.

## Fontes de dados

- `smart_system.ScheduledVisit`
- `smart_system.TechnicianSchedule`
- `smart_system.RoutePlan`
- `smart_system.TechnicianAvailabilityWindow`
- `smart_system.ServiceOrder`
- `marketplace_technicians.TechnicianAssignment`
- `marketplace_technicians.TechnicianMatchingRecord`
- `marketplace_technicians.TechnicianProfile`
- `analytics_platform.OperationalMetrics`
- `analytics_platform.TechnicianPerformance`
- `analytics_platform.AnalyticsSnapshot`

## Heuristicas implementadas

- tecnico sobrecarregado por jobs acima do limite ou carga diaria acima da capacidade
- conflitos de agenda por sobreposicao, indisponibilidade ou janela incompatível
- rota subotima com ganho relevante de deslocamento apos reordenacao simulada
- visita com risco de SLA por prioridade alta, atraso potencial ou ordem ruim na rota
- visita nao alocada com prioridade operacional
- capacidade ociosa relevante com backlog nao alocado disponivel
- redistribuicao entre tecnicos quando existe capacidade alternativa

Os limiares ficam em `AgentDefinition.config.heuristics`.

## Recommendation types

- `technician_overload`
- `route_reorder`
- `visit_reassignment`
- `sla_risk_alert`
- `unassigned_visit_attention`
- `idle_capacity_opportunity`

Cada recomendacao carrega:

- severidade
- prioridade
- resumo
- explicacao operacional
- evidencias resumidas
- acao sugerida
- score de atencao
- necessidade de aprovacao humana

## Action proposal types

- `reassign_visits_between_technicians`
- `reorder_route_plan`
- `schedule_unassigned_visit`
- `block_schedule_for_review`
- `move_visit_to_earlier_slot`
- `suggest_alternative_technician_via_matching`

## Triggers

### Event-based

- visita criada ou reprogramada
- rota reordenada
- tecnico marcado indisponivel
- OS urgente criada
- novo assignment marketplace ou mudanca de status

### Schedule-based

- `python manage.py run_scheduling_agent --mode next_day`
- `python manage.py run_scheduling_agent --mode start_of_day`
- `python manage.py run_scheduling_agent --mode weekly_routes`
- `python manage.py run_scheduling_agent --mode unassigned_backlog`

### Manual / API

- `POST /api/v1/ai-agents/manual-run/`
- `POST /api/v1/ai-agents/scheduling/run/`

## Endpoints relevantes

- `GET /api/v1/ai-agents/recommendations/?agent_slug=scheduling-agent`
- `GET /api/v1/ai-agents/recommendations/?agent_slug=scheduling-agent&site=<site_id>`
- `GET /api/v1/ai-agents/action-proposals/?agent_slug=scheduling-agent`
- `GET /api/v1/ai-agents/runs/?agent_slug=scheduling-agent`
- `GET /api/v1/ai-agents/scheduling-health/`
- `POST /api/v1/ai-agents/scheduling/run/`

## Observabilidade

Eventos especificos registrados:

- `agent.scheduling.run.started`
- `agent.scheduling.run.completed`
- `agent.scheduling.run.failed`
- `agent.scheduling.conflict.detected`
- `agent.scheduling.overload.detected`
- `agent.scheduling.recommendation.created`
- `agent.scheduling.action.proposed`
- `agent.scheduling.action.approved`
- `agent.scheduling.action.rejected`

## Interfaces administrativas

- dashboard do `AI Agents Center` com saude da agenda
- tela dedicada `Schedule Health`
- recomendacoes e propostas visiveis no fluxo comum dos agentes

## Integracoes

- `Scheduling & Routing`
- `Work Orders`
- `Preventive Maintenance`
- `Marketplace Assignments`
- `App Mobile / PWA` via atualizacao da base de `ScheduledVisit`
- `Analytics`
- `Observability`

## Limites atuais

- ETA usa heuristica local por cidade/site/estado, sem mapa externo
- especialidade do tecnico ainda influencia mais no marketplace do que na agenda interna
- a reatribuicao e proposta, nao executada automaticamente
- nao ha ainda replanejamento continuo em tempo real com telemetria do tecnico em campo

## Proximos passos recomendados

- integrar mapas/ETA reais
- otimizar multi-tecnico com algoritmo de roteirizacao mais forte
- usar atraso real do tecnico para replanejar dinamicamente
- considerar custo operacional por rota
- acoplar janela dinamica por cliente e historico de cumprimento de agenda
