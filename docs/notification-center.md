# Notification Center

## Visao do modulo

O `notification_center` e o bounded context transversal de comunicacao do SMART360. Ele centraliza canais, templates, preferencias, mensagens, notificacoes in-app, logs de entrega e lotes.

## Entidades

- `NotificationChannel`: canais disponiveis de comunicacao
- `NotificationTemplate`: templates reutilizaveis por canal
- `NotificationPreference`: preferencias por usuario ou empresa
- `NotificationEvent`: eventos internos notificaveis
- `NotificationMessage`: mensagem efetivamente gerada para envio
- `InAppNotification`: notificacao interna do sistema
- `NotificationDeliveryLog`: rastreabilidade de envio
- `NotificationBatch`: lote de disparo
- `NotificationBatchItem`: itens vinculados ao lote

## Canais suportados

- `in_app`
- `email`
- `sms`
- `whatsapp`
- `webhook`

Nesta rodada os canais sao modelados de forma generica, sem acoplamento a provedores externos reais.

## Fluxo de evento para mensagem

1. um modulo registra `NotificationEvent`
2. um template e escolhido para o canal adequado
3. `NotificationMessage` e gerada com payload renderizado
4. o status evolui entre `pending`, `sent`, `delivered` ou `failed`
5. `NotificationDeliveryLog` mantem o historico tecnico

## Fluxo de notificacao in-app

1. criar `InAppNotification`
2. usuario visualiza
3. marcar como `read`
4. opcionalmente arquivar

## Integracao com integration_bus e modulos do ecossistema

O modulo foi preparado para receber gatilhos de:

- `smart_site_factory`
- `smart_system`
- `market_core`
- `caneca_de_garagem`
- `marketplace_technicians`
- `marketplace_analytical`
- `trust_and_safety`
- `billing`
- `integration_bus`

`NotificationEvent.event_key` e `source_module` permitem conectar os fluxos sem acoplamento rigido. O proximo passo natural e usar `integration_bus` para publicar eventos e disparar envio assincrono.

## Endpoints criados

- `GET|POST /api/v1/notifications/channels/`
- `GET|POST /api/v1/notifications/templates/`
- `GET|POST /api/v1/notifications/preferences/`
- `GET|POST /api/v1/notifications/events/`
- `GET|POST /api/v1/notifications/messages/`
- `POST /api/v1/notifications/messages/{id}/mark_sent/`
- `POST /api/v1/notifications/messages/{id}/mark_delivered/`
- `POST /api/v1/notifications/messages/{id}/mark_failed/`
- `GET|POST /api/v1/notifications/in-app-notifications/`
- `POST /api/v1/notifications/in-app-notifications/{id}/mark_read/`
- `POST /api/v1/notifications/in-app-notifications/{id}/archive/`
- `GET|POST /api/v1/notifications/delivery-logs/`
- `GET|POST /api/v1/notifications/batches/`
- `GET|POST /api/v1/notifications/batch-items/`

## Proximos passos

- integrar com Celery para envio assincrono
- criar adaptadores reais para email, WhatsApp e SMS
- disparar mensagens automaticas a partir de `integration_bus`
- criar fallback de canal conforme preferencia do usuario
- adicionar tracking de abertura, clique e tentativas
