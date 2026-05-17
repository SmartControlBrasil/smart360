# Integration Bus

## Visao do modulo

O `integration_bus` e o barramento interno do SMART360 para eventos, workflows e automacoes entre bounded contexts. Ele centraliza rastreabilidade tecnica, desacoplamento entre modulos e preparacao para processamento assincrono.

## Entidades

- `IntegrationEvent`: evento registrado no barramento com payload flexivel, status, correlation id e rastreamento de publicacao/processamento
- `EventSubscription`: define consumidores de eventos por modulo e handler
- `WorkflowDefinition`: define automacoes disparadas por `trigger_event_name`
- `WorkflowExecution`: rastreia cada execucao de workflow originada por um evento
- `AutomationTask`: tarefas operacionais disparadas por workflows ou eventos
- `IntegrationLog`: trilha tecnica de logs do barramento
- `DeadLetterEvent`: eventos movidos para dead letter apos falhas repetidas

## Fluxo de eventos

1. um modulo registra um `IntegrationEvent`
2. o evento pode ser publicado no barramento
3. workflows ativos para aquele `event_name` geram `WorkflowExecution`
4. a execucao pode gerar `AutomationTask`
5. logs tecnicos sao registrados ao longo do fluxo
6. se o evento falhar repetidamente, ele vai para `DeadLetterEvent`

## Fluxo de workflows

`WorkflowDefinition` usa `trigger_event_name` e `config_json` para manter flexibilidade. Nesta primeira versao, o workflow pode gerar tarefas automaticas a partir da chave `automation_tasks`.

Exemplo:

```json
{
  "automation_tasks": [
    {
      "task_name": "create_analytics_metric",
      "task_type": "metric",
      "target_module": "analytics_platform",
      "payload": {"metric_name": "completed_service_orders"}
    }
  ]
}
```

## Automacoes

`AutomationTask` prepara o modulo para Celery e filas futuras. Os status suportados sao:

- `pending`
- `scheduled`
- `running`
- `completed`
- `failed`
- `cancelled`

## Dead letter handling

Quando um `IntegrationEvent` falha repetidamente, o barramento:

1. incrementa `retry_count`
2. registra log de erro
3. move o evento para `DeadLetterEvent` ao atingir o limite de tentativas
4. marca o evento original como `dead_letter`

## Integracao com os modulos do ecossistema

O modulo foi preparado para receber eventos de:

- `smart_system`
- `marketplace_technicians`
- `marketplace_analytical`
- `caneca_de_garagem`
- `smart_site_factory`
- `growth_engine`
- `trust_and_safety`
- `analytics_platform`
- `knowledge_engine`

## Exemplos de uso

### Service order concluida

- `smart_system` registra `service_order_completed`
- o evento e publicado
- workflow gera tarefa para `analytics_platform`

### Technician assignment aceito

- `marketplace_technicians` registra `technician_assignment_accepted`
- workflow pode disparar notificacao ou sincronizacao futura

### Site entregue

- `smart_site_factory` registra `site_delivered`
- o barramento pode encaminhar automacao para analytics ou growth

### Provider aprovado

- `trust_and_safety` podera registrar `provider_verified`
- workflows futuros poderao atualizar `marketplace_analytical` e `marketplace_technicians`

## Endpoints criados

- `GET|POST /api/v1/integration-bus/events/`
- `POST /api/v1/integration-bus/events/{id}/publish/`
- `POST /api/v1/integration-bus/events/{id}/mark_processed/`
- `POST /api/v1/integration-bus/events/{id}/mark_failed/`
- `GET|POST /api/v1/integration-bus/subscriptions/`
- `GET|POST /api/v1/integration-bus/workflow-definitions/`
- `GET|POST /api/v1/integration-bus/workflow-executions/`
- `POST /api/v1/integration-bus/workflow-executions/{id}/run/`
- `GET|POST /api/v1/integration-bus/automation-tasks/`
- `POST /api/v1/integration-bus/automation-tasks/{id}/start/`
- `POST /api/v1/integration-bus/automation-tasks/{id}/complete/`
- `POST /api/v1/integration-bus/automation-tasks/{id}/fail/`
- `GET|POST /api/v1/integration-bus/logs/`
- `GET|POST /api/v1/integration-bus/dead-letters/`

## Proximos passos

- integrar eventos reais emitidos automaticamente pelos bounded contexts
- conectar `AutomationTask` a Celery
- criar replay de dead letters e reprocessamento seguro
- adicionar handlers declarativos por assinatura
- evoluir para contratos de eventos versionados
