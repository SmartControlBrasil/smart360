# Observability

O `observability_center` agora cobre a base de observabilidade tecnica e operacional do SMART360 com separacao clara entre log tecnico, trilha de auditoria e sinais de saude da plataforma.

## Arquitetura

Camadas principais:

- `config/logging.py`
  - logging estruturado em JSON
  - mascaramento de chaves sensiveis
  - injecao de `request_id`, `correlation_id`, `company_id`, `site_id`, `user_id` e modulo
- `shared_kernel/observability/context.py`
  - contexto thread-safe/request-safe para request e tenant
- `shared_kernel/observability/middleware.py`
  - gera e propaga `X-Request-ID` e `X-Correlation-ID`
  - registra `RequestTrace`
  - consolida erro HTTP em `ErrorIncident`
- `apps/observability_center/services/observability_service.py`
  - servicos centrais de evento, incidente, metrica, health e jobs
- `apps/access_control_center/services/access_service.py`
  - auditoria funcional enriquecida com tenant, request e before/after state

## Diferenca entre Log Tecnico e Auditoria

Log tecnico:

- falhas HTTP
- incidentes
- jobs
- health
- eventos de infraestrutura/aplicacao

Auditoria funcional:

- exportacao de relatorio
- encerramento de OS
- ajuste de estoque
- alteracao de billing
- mudanca de permissao
- qualquer acao sensivel de negocio

O log tecnico vive principalmente em `SystemEventLog`, `ErrorIncident`, `MetricCounter`, `JobExecutionTrace` e `RequestTrace`.
A auditoria funcional vive em `AccessAuditLog`.

## Contexto Observavel

Quando aplicavel, os eventos passam a carregar:

- `request_id`
- `correlation_id`
- `user`
- `company`
- `site`
- `path`
- `method`
- `module`

Isso permite diagnostico com contexto multiempresa real.

## Health Checks

Endpoints:

- `/health/live/`
- `/health/ready/`
- `/health/`
- `/health/details/`
- `/api/v1/observability/health-summary/`

Checks atuais:

- Django / liveness
- banco de dados
- cache
- celery broker/backend configurados
- storage default
- disponibilidade da stack de PDF
- pending migrations

## Entidades Principais

### SystemEventLog

Evento tecnico estruturado com:

- `event_type`
- `source_module`
- `severity`
- tenant / usuario
- `request_id`
- `correlation_id`
- `entity_type` e `entity_id`
- `payload`

Exemplos:

- `work_orders.created`
- `work_orders.updated`
- `jobs.completed`
- `jobs.failed`
- `audit.reports.exported`

### ErrorIncident

Agrupa erro recorrente por `incident_key` com:

- severidade
- tenant
- request
- ultima ocorrencia
- contagem
- status

### RequestTrace

Rastro HTTP persistido contendo:

- metodo
- path
- status
- duracao
- tenant
- request id / correlation id

### JobExecutionTrace

Estado minimo de jobs e processos internos:

- inicio
- fim
- falha
- duracao
- tenant
- request

### AccessAuditLog

Auditoria funcional com:

- usuario
- company
- site
- action
- domain
- resource
- decision
- `request_id`
- `correlation_id`
- `origin`
- `before_state`
- `after_state`

## Eventos Observaveis Padronizados

Principais familias ja preparadas:

- `assets.*`
- `work_orders.*`
- `preventive.*`
- `failures.*`
- `checklists.*`
- `execution.*`
- `inventory.*`
- `reports.*`
- `auth.*`
- `permissions.*`
- `tenancy.*`
- `billing.*`
- `audit.*`
- `jobs.*`

## Endpoints

- `GET|POST /api/v1/observability/system-events/`
- `GET|POST /api/v1/observability/error-incidents/`
- `GET|POST /api/v1/observability/metric-counters/`
- `GET|POST /api/v1/observability/job-traces/`
- `GET|POST /api/v1/observability/request-traces/`
- `GET /api/v1/observability/health-summary/`
- `GET /api/v1/observability/error-summary/`
- `GET /api/v1/observability/metrics-summary/`
- `GET /api/v1/observability/platform-summary/`

## Superficie Administrativa

No `admin_shell`:

- `/app/platform-admin/observability/`

A pagina mostra:

- saude geral
- estado de dependencias
- requests recentes
- auditoria funcional
- eventos criticos
- jobs recentes
- tenants com risco financeiro

No Django admin:

- `SystemEventLog`
- `ErrorIncident`
- `MetricCounter`
- `JobExecutionTrace`
- `RequestTrace`
- `AccessAuditLog`

## Como Adicionar Novo Evento Observavel

1. Escolha `event_type` consistente, por exemplo `inventory.adjusted`.
2. Use `SystemEventService.log_system_event(...)`.
3. Para acao sensivel de negocio, use tambem `AccessAuditService.log(...)`.
4. Passe `entity_type`, `entity_id` e metadata suficiente.
5. Evite payload com segredo, token ou senha.

## Seguranca

Boas praticas aplicadas:

- chaves sensiveis mascaradas no formatter
- request headers sensiveis nao sao despejados crus
- contexto de tenant carregado sem expor segredos
- diferenca clara entre erro tecnico e acao funcional

## Evolucao Recomendada

- integrar com Sentry
- expor metricas para Prometheus
- adicionar OpenTelemetry
- incorporar alertas automaticos
- conectar incident tracking e webhooks criticos
