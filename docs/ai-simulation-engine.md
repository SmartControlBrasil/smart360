# AI Simulation Engine

O `AI Simulation Engine` e a camada de previsao operacional do SMART360. Ele compara baseline atual vs cenario proposto antes da execucao de acoes operacionais, comerciais e de agenda, produzindo um resultado explicavel, auditavel e reutilizavel pelo `AI Decision Engine`, pelos agentes e pelos copilotos.

## Objetivos

- simular impacto antes da execucao real
- comparar `current` vs `proposed`
- estimar risco, custo, SLA, margem, deslocamento e carga
- exigir simulacao para decisoes mais sensiveis
- expor resultados em API, Admin Shell e copilotos

## Arquitetura

O modulo esta implementado em `apps/ai_simulation_engine` e foi separado em cinco camadas:

- `models.py`: catalogo de tipos, cenarios, runs, resultados e trilha de auditoria
- `services/policies.py`: policy central que define quando a simulacao e opcional, recomendada ou obrigatoria
- `services/handlers.py`: handlers heuristicas por tipo de simulacao
- `services/orchestrator.py`: orquestrador central de request, baseline, execucao, persistencia e observabilidade
- `api/`: endpoints internos protegidos para request, consulta, comparacao e vinculo com decisao

## Modelo de dados

### `SimulationType`

Catalogo administrativo de tipos suportados, com `policy_mode`, `enabled` e `heuristics_config`.

### `SimulationScenario`

Cenario persistido por tenant/site/entidade alvo. Representa o contexto de simulacao.

### `SimulationRun`

Execucao concreta da simulacao, com `input_payload`, `baseline_snapshot`, status, origem, request id e vinculo opcional com `AgentDecision`.

### `SimulationResult`

Resultado comparativo consolidado com:

- `summary`
- `impact_score`
- `confidence_level`
- `risk_delta`
- `cost_delta`
- `sla_delta`
- `profit_delta`
- `travel_delta`
- `workload_delta`
- `recommendation`
- `result_payload`

### `SimulationAuditTrail`

Trilha temporal de eventos e mensagens da simulacao.

## Fluxo

1. Um agente, usuario, API ou o `AI Decision Engine` solicita uma simulacao.
2. O `SimulationOrchestrator` resolve o tipo aplicavel.
3. O handler monta o `baseline_snapshot`.
4. O handler executa heuristica deterministica e retorna comparacao.
5. O resultado e persistido em `SimulationResult`.
6. Eventos de observabilidade e auditoria sao registrados.
7. Quando houver `AgentDecision`, o resumo da simulacao e anexado no `explainability_payload`.

## Tipos suportados

- `route_reorder_simulation`
- `technician_reassignment_simulation`
- `preventive_frequency_change_simulation`
- `contract_repricing_simulation`
- `route_consolidation_simulation`
- `workload_redistribution_simulation`
- `marketplace_candidate_swap_simulation`
- `maintenance_action_plan_simulation`

## Heuristicas implementadas

### `route_reorder_simulation`

- calcula deslocamento antes/depois
- estima atraso de visitas criticas pela ordem
- usa ordenacao da `TechnicianRoutingService`

### `technician_reassignment_simulation`

- compara carga de agenda entre tecnico origem e destino
- estima risco de sobrecarga e impacto de SLA
- considera penalidade de deslocamento

### `preventive_frequency_change_simulation`

- usa historico recente de falhas do ativo
- estima aumento de custo preventivo
- estima reducao de risco operacional e corretivas provaveis

### `contract_repricing_simulation`

- calcula margem atual e margem projetada
- estima ganho de receita e delta percentual
- devolve recomendacao comercial resumida

### `route_consolidation_simulation`

- estima reducao de deslocamento com visitas na mesma regiao
- converte reducao de viagem em impacto de custo

### `workload_redistribution_simulation`

- mede pico de carga vs carga media
- estima ganho de balanceamento operacional

### `marketplace_candidate_swap_simulation`

- compara score atual vs score proposto
- considera disponibilidade e matching do marketplace

### `maintenance_action_plan_simulation`

- usa falhas recentes + backlog de ordens abertas
- estima reducao de risco vs aumento de carga/custo

## Niveis de confianca

- `high`: dados diretamente observaveis e pouca inferencia
- `medium`: heuristica com sinais operacionais confiaveis
- `low`: pouca base historica ou alto grau de aproximacao

## Policy de uso

O `SimulationPolicyService` mapeia action types do `AI Decision Engine` para simulacoes:

- `reorder_route_proposal` -> recomendada
- `create_schedule_adjustment_proposal` -> recomendada
- `create_preventive_review_task` -> obrigatoria
- `flag_contract_profitability_attention` -> obrigatoria
- `assign_marketplace_candidate_proposal` -> recomendada
- `create_work_order_proposal` -> obrigatoria
- `create_investigation_task` -> recomendada
- `mark_asset_attention` -> recomendada

Quando a simulacao e obrigatoria, a aprovacao humana e bloqueada se nao houver `SimulationRun` compativel concluido.

## Integracao com o AI Decision Engine

- `DecisionOrchestrator.receive_action_proposal` resolve requisito de simulacao e dispara run automatica quando aplicavel
- `DecisionApprovalService.approve` barra aprovacao quando a policy exige simulacao e nao existe run concluido
- o resumo da simulacao e anexado em `AgentDecision.explainability_payload`

## Integracao com agentes e copilotos

- agentes continuam propondo `ActionProposal`, mas passam a receber simulacao anexada nas decisoes suportadas
- o `ManagerCopilotService` passa a incluir simulacoes recentes em respostas sobre impacto, trade-off e cenarios
- o Admin Shell exibe um centro de simulacoes com historico recente e catalogo de tipos

## Observabilidade

Eventos emitidos:

- `simulation.requested`
- `simulation.run.started`
- `simulation.run.completed`
- `simulation.run.failed`
- `simulation.result.attached_to_decision`
- `simulation.viewed`

Cada evento carrega contexto de `request_id`, `company`, `site`, `simulation_type`, entidade, usuario e duracao quando disponivel.

## API interna

Base: `/api/v1/ai-simulations/`

- `GET /types/`
- `GET /scenarios/`
- `POST /scenarios/request/`
- `GET /runs/`
- `GET /runs/{public_id}/`
- `GET /runs/{public_id}/compare/`
- `POST /runs/{public_id}/attach_to_decision/`
- `GET /runs/by_entity/`
- `GET /runs/copilot-summary/`

## Seguranca e escopo

- acesso protegido por `ai_agents_admin`
- filtro por memberships do usuario
- simulacoes de ativos e visitas respeitam `company` e `site`
- nenhum resultado e retornado fora do tenant acessivel

## Limitacoes atuais

- heuristicas ainda sao deterministicas, sem modelo probabilistico
- alguns tipos dependem fortemente de dados preenchidos no payload da proposal
- rollback de simulacao nao se aplica porque nao ha acao operacional real
- simulacoes financeiras ainda usam margem de referencia simples

## Proximos passos

- simulation scoring probabilistico
- simulacao multi-step e multi-entidade
- simulacao financeira com custos historicos reais
- aprendizado com resultado realizado vs previsto
- batch approvals com comparacao de cenarios agregados
