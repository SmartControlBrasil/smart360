# Real-Time Event Bus + Reactive AI

## Visao Geral

O `integration_bus` passou a operar como o barramento reativo central do SMART360. A infraestrutura agora registra eventos de dominio com envelope padronizado, roteia para subscribers configurados, controla entregas com retry/dead-letter, gera logs de triggers reativos e expoe um fluxo SSE para atualizacao near real-time do `Executive War Room`.

Fluxo principal:

`mudanca operacional -> SystemEventService -> IntegrationEvent -> EventDelivery -> subscriber handler -> ReactiveTriggerLog/UI refresh/agent trigger`

## Modelagem

### IntegrationEvent

Agora representa o envelope principal do evento, com:

- `event_name`
- `event_version`
- `company`
- `site`
- `aggregate_type`
- `aggregate_id`
- `payload`
- `metadata`
- `request_id`
- `correlation_id`
- `priority`
- `occurred_at`
- `published_at`

### EventDelivery

Entrega por subscriber, com:

- `subscriber_name`
- `delivery_status`
- `attempt_count`
- `last_error`
- `delivery_payload`
- `delivered_at`

### ReactiveTriggerLog

Audita reacoes disparadas pelo barramento:

- `target_component`
- `trigger_type`
- `trigger_status`
- `summary`
- `payload`

## Catalogo Inicial

Cobertura inicial no catalogo:

- `assets.created`, `assets.updated`, `assets.status_changed`
- `work_orders.created`, `work_orders.assigned`, `work_orders.started`, `work_orders.completed`, `work_orders.reopened`, `work_orders.delayed`
- `preventive.created`, `preventive.scheduled`, `preventive.completed`, `preventive.overdue`
- `failures.created`, `failures.rca_updated`
- `checklists.started`, `checklists.completed`, `checklists.nok_detected`
- `execution.started`, `execution.updated`, `execution.completed`
- `inventory.adjusted`, `inventory.low_stock_detected`, `inventory.consumed`
- `quotes.created`, `quotes.sent`, `quotes.approved`, `quotes.rejected`
- `contracts.created`, `contracts.activated`, `contracts.suspended`, `contracts.expired`
- `billing.invoice_created`, `billing.invoice_paid`, `billing.invoice_overdue`
- `marketplace.request_created`, `marketplace.offer_received`, `marketplace.assignment_created`, `marketplace.assignment_cancelled`
- `agents.recommendation_created`, `agents.action_proposed`, `agents.anomaly_detected`
- `decision.awaiting_approval`, `decision.approved`, `decision.rejected`, `decision.executed`
- `simulation.completed`
- `briefing.generated`
- `copilot.query_received`
- `autonomy.execution_started`, `autonomy.execution_completed`, `autonomy.execution_failed`

## Subscribers e Triggers

Subscribers default seeded:

- `executive_war_room.realtime_update`
- `ai_agents_center.reactive_agent_trigger`
- `briefings.briefing_refresh`
- `copilot_context.copilot_context_refresh`

Reactive AI implementado:

- `failures.created` -> `MaintenanceAgentTriggerService.trigger_for_failure_event`
- `work_orders.delayed` -> `SchedulingAgentTriggerService.run_day_analysis`
- `billing.invoice_overdue` -> `ProfitabilityAgentTriggerService.run_company_analysis`
- `marketplace.request_created` -> `MarketplaceAllocationTriggerService.run_for_request`
- `inventory.low_stock_detected` -> `AnomalyAgentTriggerService.run_part_analysis`

Todos passam por `PolicyStudioEngine` usando o modulo `integration_bus`.

## Observabilidade

Metaeventos emitidos:

- `event.published`
- `event.delivered`
- `event.delivery_failed`
- `event.retried`
- `event.dlq_flagged`
- `reactive_trigger.fired`
- `reactive_trigger.skipped`
- `ui.realtime.updated`

Para evitar loops, os eventos internos do proprio barramento usam `_skip_event_bus`.

## Retry, Idempotencia e DLQ

- cada `EventDelivery` e unica por `integration_event + subscriber_name`
- deliveries entregues nao sao reprocessadas novamente
- retries respeitam `retry_policy.max_retries`
- ao exceder tentativas, o delivery vira `dead_letter`
- tambem e criado um `DeadLetterEvent` para inspecao operacional

## UI Reativa

Foi adicionada uma stream SSE:

- `/app/analytics/war-room/stream/`

O `Executive War Room` abre essa stream via `EventSource` e atualiza:

- intelligence feed
- contagem do feed
- contagem de decisoes pendentes

## API

Base existente ampliada em `/api/v1/integration-bus/`

Novos recursos:

- `events/<id>/chain/`
- `events/<id>/reprocess/`
- `events/intelligence_feed/`
- `deliveries/`
- `deliveries/<id>/reprocess/`
- `reactive-triggers/`

## Testes

Cobertura adicionada:

- envelope completo de evento publicado
- entregas e trigger logs
- idempotencia basica de delivery
- retry/dead-letter
- trigger reativo de agente
- escopo por tenant na API
- SSE do War Room

## Limites Atuais

- o streaming de UI esta focado no `Executive War Room`
- a estrategia de assinaturas ainda usa execution inline, sem worker dedicado
- o catalogo e amplo, mas os triggers reativos profundos estao implementados primeiro para os eventos de maior valor operacional
- nao ha websocket bidirecional; a base desta rodada usa SSE

## Proximos Passos

- ampliar SSE para `Decision Center` e outros widgets criticos
- workers dedicados para subscribers async
- regras mais ricas por prioridade e correlação
- integrações externas por webhook/event stream
- event-driven briefings automáticos mais frequentes
