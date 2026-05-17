# Anomaly Detection Agent

## Visao geral

O `Anomaly Detection Agent` e o radar transversal do `AI Agents Center`. Ele compara janelas recentes contra baselines historicas para detectar ruptura de padrao antes que o desvio vire crise operacional, financeira ou comercial.

## Arquitetura

- Agente especializado: `apps/ai_agents_center/agents/anomaly.py`
- Motor de contexto e heuristicas: `apps/ai_agents_center/services/anomaly_detection_intelligence.py`
- Gatilhos de dominio: `apps/ai_agents_center/services/anomaly_triggers.py`
- Execucao agendada: `python3 manage.py run_anomaly_agent`
- Persistencia de watchlist: `AgentAnomalyAttentionFlag`

O agente roda dentro do mesmo orquestrador dos demais agentes e reutiliza:

- `OperationalMetrics`, `ClientProfitability`, `ContractProfitability`, `TechnicianPerformance`
- `FailureEvent`, `ServiceOrder`, `StockMovement`, `ScheduledVisit`
- `TechnicianServiceRequest`, `TechnicianServiceOffer`, `TechnicianAssignment`

## Fontes de dados

- falhas por ativo e por site
- backlog operacional aberto
- SLA recente versus baseline
- corretivas por janela
- consumo de pecas e custo associado
- performance comparavel de tecnicos
- taxa de aceite/cancelamento do marketplace
- margem e lucro por contrato e cliente

## Heuristicas implementadas

- spike de falhas por ativo e por site contra media das quatro janelas anteriores
- crescimento anomalo de backlog aberto
- queda brusca de SLA ou SLA recente abaixo do patamar critico
- consumo de pecas acima da faixa historica
- piora abrupta de margem ou lucro por contrato e cliente
- comportamento de tecnico abaixo do comparavel com conflito recente
- sinais de cobertura ruim no marketplace por aceite, cancelamento ou fila sem alocacao

## Recommendation types

- `anomaly_failure_spike`
- `anomaly_backlog_growth`
- `anomaly_sla_drop`
- `anomaly_parts_consumption`
- `anomaly_technician_behavior`
- `anomaly_marketplace_signal`
- `anomaly_contract_margin_shift`
- `anomaly_site_risk_alert`

## Propostas de acao

- `open_operational_investigation`
- `trigger_maintenance_specialist_review`
- `review_parts_consumption`
- `review_marketplace_regional_coverage`
- `review_contract_profitability_shift`
- `open_operational_attention_committee`

Todas saem com human-in-the-loop no fluxo padrao do `AI Agents Center`.

## Explainability

Cada recomendacao carrega:

- entidade e escopo analisados
- baseline comparada
- desvio observado
- evidencias resumidas
- acao sugerida
- sugestao de follow-up para outro agente quando aplicavel

## API e operacao

- manual run: `POST /api/v1/ai-agents/anomaly/run/`
- health flags: `GET /api/v1/ai-agents/anomaly-health/`
- dashboard admin: `app/ai-agents/anomaly-health/`
- scheduler: `python3 manage.py run_anomaly_agent --mode daily_operations`

## Integracoes acionadas

- `smart_system.api.views`
- `smart_system.services.quote_service`
- `smart_system.services.maintenance_contract_service`
- `billing.api.views`
- `marketplace_technicians.services.marketplace_service`

## Limites atuais

- baselines ainda sao deterministicas e por janela fixa
- nao ha score probabilistico multivariado nesta versao
- o agente compara historico proprio do tenant, sem benchmark externo

## Proximos passos recomendados

- score geral de anomalia por entidade
- deteccao estatistica e multivariada
- correlacao automatica entre anomalias de dominios diferentes
- acoplamento colaborativo com `maintenance-agent`, `scheduling-agent`, `profitability-agent` e `marketplace-agent`
- alertas near real-time com ETA e notificacao executiva
