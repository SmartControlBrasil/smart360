# Scheduling Center

## Visao do modulo

O `scheduling_center` centraliza agenda, compromissos, recorrencias, disponibilidade, lembretes e tarefas temporais do ecossistema SMART360. O bounded context foi desenhado para servir operacoes de manutencao, visitas tecnicas, producao, entregas, backoffice e rotinas comerciais.

## Entidades

- `Calendar`
- `CalendarEvent`
- `EventParticipant`
- `RecurrenceRule`
- `RecurringEventLink`
- `EventOccurrence`
- `AvailabilitySlot`
- `ScheduledReminder`
- `SchedulingTask`

## Fluxo de agendamento

1. criar um `Calendar`
2. registrar um `CalendarEvent`
3. associar participantes com `EventParticipant`
4. opcionalmente vincular recorrencia com `RecurringEventLink`
5. gerar ocorrencias futuras com `EventOccurrence`
6. agendar lembretes com `ScheduledReminder`

## Recorrencia

`RecurrenceRule` suporta frequencias simples como diaria, semanal, mensal, anual e custom. `RecurringEventLink` conecta o evento pai a uma regra, e o endpoint de geracao cria `EventOccurrence` para uso operacional e futura automacao.

## Disponibilidade

`AvailabilitySlot` representa janelas reutilizaveis para tecnicos, producao, agenda comercial e operacao interna. O endpoint de disponibilidade consolida filtros por usuario, empresa, calendario e dia da semana.

## Lembretes

`ScheduledReminder` prepara o terreno para disparo futuro por `notification_center`, sem acoplamento direto nesta rodada. O modelo suporta canais como in-app, email, SMS e WhatsApp.

## Integracao com o ecossistema

O modulo foi preparado para uso por:

- `smart_system` para preventivas e visitas
- `marketplace_technicians` para janelas de atendimento
- `caneca_de_garagem` para fila de producao e entregas
- `smart_site_factory` para revisoes e entregas
- `backoffice` para agenda interna
- `notification_center` para lembretes
- `reporting_center` para historico e extracoes futuras

## Endpoints criados

- `GET|POST /api/v1/scheduling/calendars/`
- `GET|POST /api/v1/scheduling/events/`
- `GET|POST /api/v1/scheduling/participants/`
- `GET|POST /api/v1/scheduling/recurrence-rules/`
- `GET|POST /api/v1/scheduling/recurring-links/`
- `POST /api/v1/scheduling/recurring-links/{id}/generate-occurrences/`
- `GET|POST /api/v1/scheduling/occurrences/`
- `GET|POST /api/v1/scheduling/availability-slots/`
- `GET|POST /api/v1/scheduling/reminders/`
- `GET|POST /api/v1/scheduling/tasks/`
- `GET /api/v1/scheduling/calendar-view/`
- `GET /api/v1/scheduling/upcoming-events/`
- `GET /api/v1/scheduling/my-tasks/`
- `GET /api/v1/scheduling/availability/`

## Proximos passos

- gerar eventos recorrentes reais em background com Celery
- integrar lembretes com `notification_center`
- adicionar sincronizacao futura com calendarios externos
- criar politicas de conflito e capacidade por recurso
