# Profitability Agent

O `Profitability Agent` e a inteligencia economico-operacional do `AI Agents Center` para detectar erosao de margem e sugerir acoes gerenciais com rastreabilidade.

## Arquitetura

- Agente especializado: `apps/ai_agents_center/agents/profitability.py`
- Motor deterministico: `apps/ai_agents_center/services/profitability_intelligence.py`
- Triggers: `apps/ai_agents_center/services/profitability_triggers.py`
- Persistencia de watchlist economica: `AgentProfitabilityAttentionFlag`
- Execucao agendada: `python3 manage.py run_profitability_agent`

## Fontes de dados

- `analytics_platform.ClientProfitability`
- `analytics_platform.ContractProfitability`
- `analytics_platform.TechnicianPerformance`
- `analytics_platform.OperationalMetrics`
- `smart_system.ServiceOrder`
- `smart_system.WorkLog`
- `smart_system.StockMovement`
- `smart_system.ScheduledVisit`
- `smart_system.ServiceQuote`
- `smart_system.MaintenanceContract`

## Heuristicas implementadas

- cliente com margem abaixo do minimo saudavel
- cliente com lucro negativo em sequencia recente
- contrato deficitario ou abaixo do minimo de margem
- contrato com excesso de corretivas versus preventivas
- atendimento com custo executado acima da receita atribuida
- atendimento com desvio relevante versus orcamento aprovado
- rota/regiao com deslocamento corroendo margem
- tecnico com profit medio por OS abaixo da referencia comparavel

## Recommendation types

- `client_margin_alert`
- `contract_profitability_risk`
- `excessive_service_cost`
- `route_margin_erosion`
- `technician_efficiency_attention`
- `repricing_recommendation`
- `scope_review_recommendation`
- `profitability_watch`

## Action proposals

- `review_client_in_management_committee`
- `suggest_contract_repricing`
- `suggest_scope_recalibration`
- `suggest_route_consolidation`
- `prioritize_preventive_to_reduce_corrective_cost`
- `create_recurring_profitability_alert`

## Triggers

### Event-based

- criacao/atualizacao de OS
- aprovacao de orcamento
- ativacao, suspensao, expiracao e billing de contrato recorrente
- criacao/atualizacao de `WorkLog`
- criacao/atualizacao de `Invoice` e `billing.Contract`

### Scheduled

- `run_profitability_agent --mode monthly_clients`
- `run_profitability_agent --mode weekly_contracts`
- `run_profitability_agent --mode monthly_margin`
- `run_profitability_agent --mode regional_operation`

### Manual/API

- `POST /api/v1/ai-agents/profitability/run/`
- filtros por cliente, contrato, tecnico e site
- `GET /api/v1/ai-agents/profitability-health/`

## Explainability

Cada recomendacao grava:

- resumo executivo
- explicacao gerencial
- evidencias resumidas
- acao sugerida
- score de atencao
- payload auditavel com sinais observados

## Limitacoes atuais

- custos de deslocamento usam estimativa operacional, nao ETA real
- comparacao regional ainda e baseada em site/unidade
- o agente nao executa reajuste automaticamente
- o racional e deterministico; nao ha previsao probabilistica de margem futura nesta versao

## Proximos passos

- score economico historico por cliente/contrato
- simulacao de reajuste e revisao de escopo
- comparacao entre regioes e squads
- previsao de erosao de margem
- uso de ETA/mapas reais para custo de rota
