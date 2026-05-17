# Agenda e Roteirizacao de Tecnicos

## Visao geral

O modulo de agenda do SMART360 organiza visitas tecnicas em uma camada operacional unica, independente da origem do atendimento:

- ordem de servico
- preventiva
- assignment do marketplace
- visita manual

Todas as fontes convergem para `ScheduledVisit`, que pode ser planejada, roteirizada e consumida no shell operacional e no app/PWA tecnico.

## Entidades principais

- `TechnicianAvailabilityWindow`
  disponibilidade, bloqueios e capacidade diaria por tecnico
- `TechnicianSchedule`
  resumo consolidado de carga por tecnico e data
- `RoutePlan`
  plano de rota gerado para o tecnico em uma data
- `ScheduledVisit`
  visita operacional individual com vinculos para OS, preventiva ou assignment

## Heuristica de roteirizacao v1

A v1 usa uma heuristica deterministica e transparente:

1. atualiza visitas planejaveis da data
2. ordena por prioridade operacional
3. respeita janela inicial de atendimento quando existir
4. estima deslocamento por:
   - mesmo site
   - mesma cidade
   - mesmo estado
   - outro estado
5. detecta conflitos:
   - overlap
   - before_window
   - after_window
   - technician_unavailable
   - blocked_period
   - daily_jobs_exceeded
   - daily_hours_exceeded

## Integracoes

- `ServiceOrder`
  visitas operacionais corretivas/inspecoes
- `MaintenancePlan`
  fila preventiva ainda nao alocada
- `TechnicianAssignment`
  atendimento originado no marketplace
- `TechnicianProfile` e matching
  sugerem tecnico quando a visita ainda nao foi alocada
- PWA tecnico
  exibe agenda do dia e proxima visita
- observabilidade
  eventos `schedule.visit.updated`, `schedule.conflict.detected` e `route.generated`

## APIs internas

Registradas em `apps/smart_system/api/urls.py`:

- `technician-availability`
- `technician-schedules`
- `route-plans`
- `scheduled-visits`

Acoes customizadas:

- `scheduled-visits/by-technician/`
- `scheduled-visits/by-date/`
- `scheduled-visits/unassigned/`
- `scheduled-visits/reorder/`

## Shell e PWA

Shell:

- `/app/smart-system/scheduling/`
- `/app/smart-system/scheduling/calendar/`
- `/app/smart-system/scheduling/technicians/<id>/`
- `/app/smart-system/scheduling/unassigned/`

PWA tecnico:

- `/field/schedule/`

## Limitacoes atuais

- a distancia ainda usa heuristica por site/cidade/estado, sem mapa externo
- nao existe drag and drop visual no shell nesta rodada
- preventivas usam `MaintenancePlan.next_due_date` como fonte inicial, sem entidade dedicada de execucao agendada
- a sugestao automatica de tecnico ainda e heuristica, nao otimizada por solver

## Proximos passos recomendados

- integrar mapas/ETA real
- suportar reordenacao visual da rota
- adicionar janelas complexas e SLA por cliente
- evoluir para balanceamento automatico multi-tecnico
- sincronizar agenda detalhada com notificacoes e app offline
