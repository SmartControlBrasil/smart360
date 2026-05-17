# AI Decision Engine

## Objetivo
O AI Decision Engine e a camada central de governanca entre agentes, copilotos, aprovadores humanos e modulos operacionais. Ele recebe `ActionProposal`, classifica risco e escopo, aplica policy, decide o caminho de autonomia e executa apenas acoes permitidas com trilha completa.

## Fluxo
1. Um agente grava `AgentActionProposal`.
2. `DecisionOrchestrator.receive_action_proposal()` normaliza o `action_type`, classifica risco e tenant impact.
3. `DecisionPolicyEngine` resolve a `DecisionPolicy` aplicavel.
4. O engine materializa `AgentDecision` e registra explainability.
5. A decisao segue um dos fluxos:
   - `auto_approved` + `executed`
   - `awaiting_approval`
   - `escalated`
   - `auto_blocked`
6. `DecisionExecutionService` chama o handler dedicado quando a execucao e permitida.
7. `DecisionApproval`, `DecisionExecution` e `DecisionAuditTrail` preservam a trilha completa.

## Modelagem
- `DecisionPolicy`: policy por `action_type`, risco, autonomia, tenant scope e roles aprovadoras.
- `AgentDecision`: decisao materializada para cada proposal, com explainability e status consolidado.
- `DecisionApproval`: aprovacoes humanas, comentarios e perfis requeridos.
- `DecisionExecution`: tentativas de execucao, resultado, erro, duracao e rollback.
- `DecisionAuditTrail`: eventos cronologicos do ciclo de vida da decisao.

## Catalogo Inicial De Action Types
- `create_work_order_proposal`
- `create_preventive_review_task`
- `mark_asset_attention`
- `create_schedule_adjustment_proposal`
- `reorder_route_proposal`
- `assign_marketplace_candidate_proposal`
- `flag_contract_profitability_attention`
- `create_investigation_task`
- `escalate_operational_alert`

## Mapeamento Dos Agentes
O classifier normaliza os action types legados dos agentes para o catalogo canonico do engine. Exemplos:
- `open_inspection_work_order` -> `create_work_order_proposal`
- `mark_asset_under_watch` -> `mark_asset_attention`
- `reorder_route_plan` -> `reorder_route_proposal`
- `suggest_alternative_technician_via_matching` -> `assign_marketplace_candidate_proposal`
- `review_contract_profitability_shift` -> `flag_contract_profitability_attention`
- `open_operational_investigation` -> `create_investigation_task`

## Matriz De Risco E Autonomia
- `low`: reversivel e nao destrutivo; elegivel para Level 2 seguro.
- `medium`: impacto operacional moderado; por padrao revisavel.
- `high`: altera agenda, OS ou alocacao; exige aprovacao humana.
- `critical`: contratual/comercial/estrutural; escala obrigatoria nesta rodada.

- Level 0: reservado para recomendacao pura.
- Level 1: proposal com aprovacao humana.
- Level 2: autoexecucao apenas para flag segura, investigacao interna e materializacao controlada.
- Level 3: nao habilitado por default; base pronta para expansao futura.

## Policies Implementadas
- Work order proposal: risco alto, site-scoped, aprovacao humana.
- Preventive review task: risco medio, site-scoped, aprovacao humana.
- Mark asset attention: risco baixo, autoexecucao segura.
- Schedule adjustment proposal: risco alto, aprovacao de coordenacao.
- Reorder route proposal: risco medio, aprovacao de coordenacao.
- Assign marketplace candidate proposal: risco alto, aprovacao humana.
- Profitability attention flag: risco medio, autoexecucao segura; cenarios criticos escalam.
- Investigation task: risco baixo, autoexecucao segura.
- Escalate operational alert: risco medio, aprovacao humana.

## Handlers De Execucao
- `CreateWorkOrderHandler`
- `CreatePreventiveReviewTaskHandler`
- `MarkAssetAttentionHandler`
- `CreateScheduleAdjustmentHandler`
- `ReorderRouteProposalHandler`
- `AssignMarketplaceCandidateHandler`
- `FlagContractProfitabilityAttentionHandler`
- `CreateInvestigationTaskHandler`
- `EscalateOperationalAlertHandler`

## Observabilidade
Eventos emitidos:
- `decision.received`
- `decision.policy.applied`
- `decision.awaiting_approval`
- `decision.approved`
- `decision.rejected`
- `decision.auto_approved`
- `decision.auto_blocked`
- `decision.execution.started`
- `decision.execution.succeeded`
- `decision.execution.failed`

Payload minimo:
- `request_id`
- `company`
- `site`
- `action_type`
- `entity_type`
- `entity_id`
- `agent`
- `user`
- `policy`
- `duration_ms`

## UI E Operacao
- API protegida em `/api/v1/ai-decisions/`.
- Centro administrativo no shell em `/app/ai-agents/decisions/`.
- Manager Copilot agora exibe decisoes pendentes com a mesma capacidade de aprovar/rejeitar.

## Limitacoes Atuais
- Rollback esta modelado, mas so alguns handlers marcam suporte futuro.
- Multi-step approval ainda nao foi ativado.
- Policies por tenant/segmento ainda compartilham catalogo default.
- Simulation mode e score numerico de decisao ainda nao foram implementados.

## Proximos Passos Recomendados
- Aprovações em lote e SLA de approvals.
- Policy simulation para validar autonomia por tenant.
- Multi-step approvals para decisoes criticas.
- Rollback operacional real para agenda e marketplace.
- Score quantitativo de confianca da decisao.
