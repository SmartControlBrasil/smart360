# Marketplace Allocation Agent

O `Marketplace Allocation Agent` e o dispatcher inteligente do marketplace no `AI Agents Center`.

## Arquitetura

- Agente especializado: `apps/ai_agents_center/agents/marketplace.py`
- Motor deterministico: `apps/ai_agents_center/services/marketplace_allocation_intelligence.py`
- Triggers: `apps/ai_agents_center/services/marketplace_triggers.py`
- Watchlist persistida: `AgentMarketplaceRequestFlag`
- Execucao agendada: `python3 manage.py run_marketplace_agent`

## Fontes de dados

- `marketplace_technicians.TechnicianServiceRequest`
- `marketplace_technicians.TechnicianMatchingRecord`
- `marketplace_technicians.TechnicianAssignment`
- `marketplace_technicians.TechnicianServiceOffer`
- `marketplace_technicians.TechnicianProfile`
- `marketplace_technicians.TechnicianAvailability`
- `smart_system.ScheduledVisit`
- `smart_system.TechnicianAvailabilityWindow`

## Heuristicas implementadas

- melhor candidato = match score alto + viabilidade real
- score alto sem agenda/disponibilidade vira conflito operacional
- request urgente penaliza distancia alta
- sobrecarga de agenda penaliza ou invalida candidato
- perfil nao verificado ou offline invalida candidato
- historico baixo de aceite penaliza viabilidade
- request sem candidatos viaveis gera fallback
- request perto do SLA gera alerta de alocacao

## Recommendation types

- `technician_allocation_recommendation`
- `no_viable_candidate_alert`
- `sla_allocation_risk`
- `fallback_assignment_recommendation`
- `technician_unavailable_conflict`
- `marketplace_request_attention`

## Action proposals

- `assign_recommended_marketplace_technician`
- `reassess_candidate_due_unavailability`
- `activate_marketplace_fallback`
- `redistribute_technician_agenda_for_request`
- `adjust_marketplace_request_window`
- `escalate_marketplace_request_attention`

## Triggers

### Event-based

- criacao de `TechnicianServiceRequest`
- refresh de matching
- criacao/rejeicao/withdraw de offer
- criacao e transicao de assignment

### Scheduled

- `run_marketplace_agent --mode open_requests`
- `run_marketplace_agent --mode unassigned_requests`
- `run_marketplace_agent --mode sla_risk`
- `run_marketplace_agent --mode regional_backlog`

### Manual/API

- `POST /api/v1/ai-agents/marketplace/run/`
- `GET /api/v1/ai-agents/marketplace-health/`

## Explainability

Cada recomendacao armazena:

- motivo operacional da escolha
- comparacao entre candidatos
- restricoes de agenda/disponibilidade
- risco de SLA
- alternativas e acao sugerida

## Limitacoes atuais

- usa distancia estimada do matching, nao ETA de mapa em tempo real
- historico do tecnico usa sinais disponiveis na base atual
- fallback e proposto, nao executado automaticamente
- colaboracao direta com Scheduling Agent fica preparada, mas ainda nao invoca simulacao entre agentes

## Proximos passos

- alocacao automatica controlada
- previsao probabilistica de aceite e no-show
- ETA real por mapa/regiao
- colaboracao direta com Scheduling Optimization Agent
- analise regional para expansao de base tecnica
