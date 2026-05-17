# Backoffice

## Visao do modulo

O `backoffice` e a camada operacional interna do SMART360 para filas, alertas, tarefas, widgets e quick actions. Ele nao substitui o Django admin; ele prepara um cockpit administrativo proprio para a equipe interna.

## Entidades

- `BackofficeQueue`: agrupamentos operacionais por modulo
- `BackofficeQueueItem`: itens de fila com prioridade e atribuicao
- `BackofficeAlert`: alertas operacionais e criticos
- `BackofficeTask`: tarefas internas de acompanhamento
- `BackofficeQuickAction`: acoes rapidas configuraveis para o cockpit
- `BackofficeWidget`: widgets do dashboard administrativo
- `BackofficeNote`: notas operacionais vinculadas a itens externos

## Filas

As filas servem para consolidar pendencias como:

- verificacoes pendentes
- pedidos em producao
- invoices overdue
- ordens de servico abertas
- tecnicos aguardando aprovacao

## Alertas

Os alertas permitem representar itens criticos de varios modulos, com severidade `info`, `warning` e `critical`, alem de status de resolucao.

## Tarefas

`BackofficeTask` suporta atribuicao interna, prioridade, prazo e vinculo generico com qualquer item externo do ecossistema.

## Dashboard operacional

O endpoint `GET /api/v1/backoffice/dashboard/` consolida:

- filas ativas com contagem de itens
- alertas criticos em aberto
- tarefas pendentes ou em progresso
- widgets ativos
- quick actions ativas

## Integracoes com modulos do ecossistema

O modulo foi preparado para integrar com:

- `trust_and_safety`
- `smart_site_factory`
- `smart_system`
- `marketplace_technicians`
- `marketplace_analytical`
- `caneca_de_garagem`
- `billing`
- `notification_center`
- `analytics_platform`
- `integration_bus`

O vinculo com itens externos usa `item_type` e `item_id` para manter desacoplamento.

## Endpoints criados

- `GET|POST /api/v1/backoffice/queues/`
- `GET|POST /api/v1/backoffice/queue-items/`
- `GET|POST /api/v1/backoffice/alerts/`
- `GET|POST /api/v1/backoffice/tasks/`
- `GET|POST /api/v1/backoffice/quick-actions/`
- `GET|POST /api/v1/backoffice/widgets/`
- `GET|POST /api/v1/backoffice/notes/`
- `GET /api/v1/backoffice/dashboard/`

## Proximos passos

- criar conectores automaticos com `integration_bus`
- popular filas e alertas a partir de eventos reais do ecossistema
- adicionar SLA e ownership por equipe
- criar snapshots operacionais para `analytics_platform`
- preparar frontend administrativo proprio
