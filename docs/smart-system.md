# SMART SYSTEM

## Visao do modulo

O Smart System e o bounded context de manutencao, ativos, ordens de servico, preventivas, checklists, falhas e rastreabilidade operacional do ecossistema SMART360.

## Entidades

- `MaintenanceClient`
- `OperationalSite`
- `AssetCategory`
- `Asset`
- `MaintenancePlan`
- `Checklist`
- `ChecklistItem`
- `ServiceOrder`
- `ServiceOrderChecklistResponse`
- `FailureEvent`
- `AssetHistoryEvent`
- `WorkLog`
- `ServiceDocument`

## Fluxo operacional

1. Cadastrar cliente e unidades operacionais.
2. Cadastrar categorias e ativos.
3. Configurar planos preventivos e checklists.
4. Abrir ordens de servico manuais, por falha ou por preventiva.
5. Registrar execucao, checklist, apontamento e documentos.
6. Concluir OS e manter historico completo do ativo.

## Fluxo corretivo

1. Falha e registrada no ativo.
2. O time abre ou vincula uma OS corretiva.
3. A execucao gera work logs, evidencias e conclusao.
4. O ativo recebe historico automatico da falha e da OS.

## Fluxo preventivo

1. Plano preventivo e configurado por ativo ou categoria.
2. Checklist opcional e associado ao plano.
3. A estrutura fica pronta para futura geracao automatica de OS recorrentes.

## Endpoints

- `GET|POST /api/v1/smart-system/clients/`
- `GET|POST /api/v1/smart-system/sites/`
- `GET|POST /api/v1/smart-system/asset-categories/`
- `GET|POST /api/v1/smart-system/assets/`
- `GET|POST /api/v1/smart-system/maintenance-plans/`
- `GET|POST /api/v1/smart-system/checklists/`
- `GET|POST /api/v1/smart-system/checklist-items/`
- `GET|POST /api/v1/smart-system/service-orders/`
- `GET|POST /api/v1/smart-system/service-order-checklist-responses/`
- `GET|POST /api/v1/smart-system/failure-events/`
- `GET|POST /api/v1/smart-system/asset-history-events/`
- `GET|POST /api/v1/smart-system/work-logs/`
- `GET|POST /api/v1/smart-system/attachments/`

## Proximos passos de evolucao

- geracao automatica de preventivas por calendario
- calculo de MTBF, MTTR e disponibilidade
- backlog e SLA por prioridade
- analise de falhas e RCA estruturado
- dashboards operacionais e KPIs de manutencao
