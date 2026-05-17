# Analytics Platform

## Visao do modulo

O `analytics_platform` agora cobre duas camadas complementares:

- a camada analitica generica do ecossistema, com eventos, metricas, dashboards e snapshots
- a camada executiva operacional, com rentabilidade, produtividade, SLA e leitura financeira por empresa

Essa segunda camada foi desenhada para dar suporte a gestores operacionais, financeiro, auditoria e futuras automacoes orientadas por IA.

## Modelagem executiva

Foram adicionadas quatro entidades persistidas para consolidacao periodica:

- `OperationalMetrics`
- `ClientProfitability`
- `ContractProfitability`
- `TechnicianPerformance`

Essas entidades armazenam snapshots por `company`, `period_type` e `period_start`, permitindo leitura historica sem recalcular tudo a cada acesso.

## Fontes de dados usadas

Os calculos executivos usam dados de:

- `ServiceOrder`
- `WorkLog`
- `StockMovement`
- `ServiceQuote`
- `MaintenanceContract`
- `Invoice`
- `TechnicianProfile`
- `TechnicianReview`

Com isso, a leitura analitica combina receita, custo, produtividade e SLA em uma base coerente.

## KPIs executivos implementados

O dashboard executivo expoe, no minimo:

- contratos ativos
- MRR total
- receita do periodo
- custo operacional
- lucro operacional
- margem
- SLA medio
- tempo medio de resposta
- tempo medio de execucao

Tambem foram adicionadas visoes auxiliares de:

- receita por periodo
- lucro por periodo
- clientes mais lucrativos
- contratos mais lucrativos
- tecnicos mais produtivos
- ativos mais problematicos
- alertas executivos

## Custos considerados

A camada atual calcula custo operacional a partir de:

- mao de obra estimada via `WorkLog`
- consumo de pecas via `StockMovement`
- deslocamento estimado

Os multiplicadores padrao ficam centralizados em `ExecutiveAnalyticsService` e podem ser ajustados sem quebrar o contrato da API.

## SLA e produtividade

O SLA atual usa alvo por prioridade da OS:

- `low`: 1440 min
- `medium`: 480 min
- `high`: 240 min
- `urgent`: 120 min

Para produtividade tecnica, o modulo consolida:

- jobs concluidos
- tempo medio de execucao
- nota media do tecnico
- receita, custo e lucro gerados

## API implementada

Endpoints executivos adicionados:

- `GET /api/v1/analytics/executive/overview/`
- `POST /api/v1/analytics/executive/refresh/`
- `GET /api/v1/analytics/revenue/`
- `GET /api/v1/analytics/profitability/`
- `GET /api/v1/analytics/technicians/`
- `GET /api/v1/analytics/assets/`

Viewsets adicionais:

- `GET|POST /api/v1/analytics/operational-metrics/`
- `GET|POST /api/v1/analytics/client-profitability/`
- `GET|POST /api/v1/analytics/contract-profitability/`
- `GET|POST /api/v1/analytics/technician-performance/`

Todos esses endpoints respeitam:

- autenticacao
- RBAC por `analytics_admin.*`
- scoping por empresa

## Admin Shell

O shell interno passou a expor:

- `GET /app/analytics/executive/`
- `GET /app/analytics/executive/refresh/`

A pagina executiva mostra graficos de receita e lucro, leaderboard tecnico, contratos/clientes mais lucrativos, analise de ativos e alertas de operacao.

## Permissoes

O modulo usa o dominio `analytics_admin`, com acoes:

- `view`
- `manage`
- `export`

Perfis com leitura executiva inicial:

- `super-admin`
- `company-admin`
- `maintenance-manager`
- `planner`
- `auditor-readonly`
- `finance-readonly`

Perfis tecnicos e de almoxarifado nao recebem acesso executivo por padrao.

## Integracao com observabilidade

O refresh executivo registra:

- auditoria via `AccessAuditService`
- evento tecnico via `SystemEventService`
- snapshot consolidado em `AnalyticsSnapshot`

Isso prepara trilha historica e explicabilidade operacional para futuras automacoes.

## Preparacao para IA

O modelo foi estruturado para alimentar agentes futuros de:

- recomendacao de contratos
- deteccao de clientes deficitarios
- sugestao de reajuste de precificacao
- priorizacao de ativos problematicos
- balanceamento de carga tecnica
- deteccao de anomalias em SLA e margem

Os snapshots periodicos evitam que agentes dependam apenas de consultas operacionais brutas.

## Proximos passos

- automatizar refresh periodico via Celery
- adicionar series trimestrais e anuais mais ricas no shell
- expor exportacao estruturada para BI externo
- calibrar custos com dados reais de deslocamento e hora tecnica
- integrar alertas executivos ao `notification_center` e ao `backoffice`
