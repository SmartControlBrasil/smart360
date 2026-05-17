# Autonomous Operations Mode

## Objetivo

O `Autonomous Operations Mode` fecha a ponte entre recomendacao inteligente e execucao real controlada. Ele permite que o SMART360 autoexecute apenas acoes operacionais de baixo risco e explicitamente elegiveis, sob policy, safety envelope, confidence threshold, simulacao previa quando necessaria, rollback e trilha auditavel.

Fluxo principal:

`proposal -> decision engine -> policy studio -> safety envelope -> simulation check -> guards -> execute -> observe -> optimization loop`

## Arquitetura

App principal: `apps/ai_autonomous_ops`

Componentes:

- `AutonomousModeConfig`: habilitacao por tenant, mode level, risco maximo, action types elegiveis, thresholds e kill switch.
- `AutonomousExecution`: registro da autoexecucao, snapshot de policy/guards, confidence, simulation, resultado e rollback.
- `AutonomousExecutionGuard`: limites configuraveis de volume, falha, rollback, confidence e kill switch.
- `AutonomousIncident`: incidentes de autonomia para investigacao, war room e governanca.
- `AutonomousAuditTrail`: trilha cronologica da autonomia.

Servicos:

- `AutonomousPolicyService`: resolve config efetiva e valida o safety envelope.
- `AutonomousGuardService`: impede runaway automation por volume, falha, rollback, incidentes e confidence floor.
- `AutonomousOperationsService`: pipeline central de candidatura, simulacao, execucao, bloqueio e integracao.
- `AutonomousRollbackService`: reversao auditada para acoes suportadas.
- `AutonomousHealthService`: indicadores de saude da autonomia.

## Safety Envelope

Uma acao so pode autoexecutar se todos os checks forem verdadeiros:

- tenant com autonomia habilitada
- `mode_level` compativel com o risco da acao
- `action_type` permitido e nao bloqueado
- risco dentro de `max_risk_level`
- kill switch global/tenant/agente/action type desligado
- confidence acima do threshold efetivo
- simulacao disponivel e favoravel quando exigida
- sem guard violation
- sem policy de aprovacao obrigatoria remanescente

## Catalogo Inicial Elegivel

Acoes elegiveis nesta rodada:

- `mark_asset_attention`
- `create_investigation_task`
- `flag_contract_profitability_attention`
- `reorder_route_proposal`

Acoes explicitamente bloqueadas nesta rodada:

- `create_work_order_proposal`
- `create_schedule_adjustment_proposal`
- `assign_marketplace_candidate_proposal`
- `escalate_operational_alert`

## Niveis de Autonomia

- `Mode 0`: desabilitado
- `Mode 1`: somente recomendacao
- `Mode 2`: autoexecucao de low-risk explicitas
- `Mode 3`: base para low + algumas medium com simulacao e confidence alta

Nesta versao, a base operacional foi consolidada para `Mode 1` e `Mode 2`, com suporte inicial governado para `Mode 3`.

## Integracoes

### Decision Engine

O `DecisionOrchestrator` encaminha candidatos autoexecutaveis para `AutonomousOperationsService.evaluate_and_execute`. Se o envelope bloquear, a decisao volta para `awaiting_approval`.

### Policy Studio

O runtime de autonomia passa por avaliacoes `evaluate_candidate`, `execute_autonomy` e `rollback_autonomy`.

### Simulation Engine

Quando o `action_type` exige simulacao, o motor roda `SimulationOrchestrator.simulate_for_decision`. Sem simulacao concluida, a autonomia e bloqueada.

### Auto-Optimization Loop

Como a execucao final ainda passa pelo `DecisionExecutionService`, outcomes, scoring e proposals de melhoria continuam sendo medidos pelo loop de otimizacao.

### Executive War Room / Admin Shell

O shell expone o cockpit em `/app/ai-agents/autonomy/`, com:

- saude da autonomia
- configuracoes ativas
- autoexecucoes recentes
- guards
- incidentes recentes

## Observabilidade

Eventos principais:

- `autonomy.candidate.received`
- `autonomy.policy.allowed`
- `autonomy.policy.blocked`
- `autonomy.simulation.required`
- `autonomy.simulation.passed`
- `autonomy.simulation.failed`
- `autonomy.execution.started`
- `autonomy.execution.succeeded`
- `autonomy.execution.failed`
- `autonomy.rollback.started`
- `autonomy.rollback.succeeded`
- `autonomy.kill_switch.activated`
- `autonomy.incident.created`

## API

Base: `/api/v1/ai-autonomy/`

Recursos:

- `configs/`
- `executions/`
- `incidents/`
- `guards/`

Acoes:

- `POST /configs/<public_id>/kill_switch/`
- `POST /executions/<public_id>/rollback/`
- `GET /executions/health/`

## Testes

Cobertura adicionada:

- autoexecucao low-risk bem-sucedida
- bloqueio por policy
- bloqueio por confidence baixo
- bloqueio quando simulacao obrigatoria nao esta disponivel
- kill switch
- rollback suportado
- incidente em falha de execucao
- API de listagem, health e rollback
- escopo multiempresa na API

## Limitacoes Atuais

- medium-risk autonomo ainda depende de enablement explicito e configuracao cuidadosa
- rollback cobre apenas os action types reversiveis implementados
- confidence ainda e heuristico, nao probabilistico
- guards usam janelas simples de volume/falha/rollback, sem tuning adaptativo ainda

## Proximos Passos

- kill switch global dedicado fora da configuracao do tenant
- autonomia por janela horaria e por dominio
- incident correlation no War Room
- rollback automatico supervisionado por outcome ruim
- confidence score calibrado com historico real e simulacao vs realizado
