# AI Auto-Optimization Loop

O `Auto-Optimization Loop` fecha o ciclo supervisionado do SMART360 entre recomendacao, decisao, simulacao, execucao e resultado observado. O objetivo nao e criar autoaprendizado opaco, e sim aprendizado operacional auditavel, explicavel e aprovavel.

## Escopo entregue

- outcomes para recomendacoes, decisoes e simulacoes
- feedback explicito e implicito
- scoring de efetividade numerico e categorico
- propostas de ajuste supervisionado
- policies de aprendizado e aprovacao
- aplicacao controlada de ajustes
- dashboard de qualidade no Admin Shell
- APIs protegidas para feedback, outcomes, proposals e quality

## Arquitetura

O modulo foi implementado em `apps/ai_optimization_loop` com as seguintes camadas:

- `models.py`: outcomes, feedbacks, policies, proposals e trilha de auditoria
- `services/outcomes.py`: comparacao expected vs actual e scoring
- `services/feedback.py`: captura de feedback explicito
- `services/proposals.py`: geracao de optimization proposals
- `services/approvals.py`: aprovacao/rejeicao supervisionada
- `services/appliers.py`: aplicacao controlada dos ajustes aprovados
- `services/orchestrator.py`: orquestracao central do loop
- `services/quality.py`: agregacoes de qualidade por agente e copilot
- `api/`: endpoints internos protegidos

## Modelo de dados

### `RecommendationOutcome`

Fecha o ciclo de uma `AgentRecommendation` com:

- expectativa original
- efeito observado
- score de efetividade
- nivel categorizado

### `DecisionOutcome`

Fecha o ciclo de uma `AgentDecision` apos tentativa de execucao:

- status real
- expectativa original
- resultado atual
- score de efetividade
- resumo avaliativo

### `SimulationOutcome`

Compara simulacao prevista com resultado observado da decisao relacionada:

- expected result
- actual result
- aderencia prevista vs realizada

### `FeedbackSignal`

Captura feedback explicito e implicito para:

- recommendation
- decision
- simulation
- copilot message
- agent

### `OptimizationPolicy`

Define quais ajustes podem ser sugeridos e como sao aprovados.

### `OptimizationProposal`

Representa uma proposta supervisionada de ajuste com:

- alvo
- valor atual
- valor proposto
- rationale
- evidencia
- impacto esperado
- risco
- status

## Fluxo operacional

1. O agente gera recommendation/proposal.
2. O `Decision Engine` decide e pode executar.
3. O `Simulation Engine` estima impacto antes da acao.
4. O `Auto-Optimization Loop` mede o outcome real apos execucao.
5. Feedback explicito e implicito e agregado.
6. O score de efetividade e recalculado.
7. Quando cabivel, uma `OptimizationProposal` e gerada.
8. O ajuste so e aplicado apos aprovacao supervisionada.

## Feedback suportado

### Explicito

- utilidade de recomendacao
- qualidade de decisao
- confianca em simulacao
- utilidade de resposta do copilot

### Implicito

- sucesso/falha da execucao
- materializacao de artefato operacional
- aderencia entre simulacao e resultado real
- sinais agregados de baixa efetividade por agente

## Score de efetividade

O score vai de `0` a `100` e e traduzido para:

- `very_effective`
- `effective`
- `neutral`
- `weak`
- `harmful`

O score usa:

- base por status observado
- bonus por artefato operacional confirmado
- ajuste por feedback humano medio

## Tipos de ajuste suportados

- `approval_requirement_adjustment` em `DecisionPolicy`
- `heuristic_config_adjustment` em `SimulationType`
- `ranking_adjustment` em `AgentExecutionPolicy`
- `ranking_adjustment` em `ManagerCopilotConfiguration`

## Regras implementadas nesta rodada

### Decisao ruim em policy autoexecutavel

Quando uma decisao autoexecutada falha e sua policy nao exigia aprovacao humana, o loop sugere:

- elevar `requires_human_approval`
- reduzir autonomia efetiva

### Simulacao com baixa aderencia

Quando a simulacao entrega baixa efetividade observada, o loop sugere:

- ampliar `observation_window_days`
- ativar `confidence_guardrail`

### Agente com score composto baixo

Quando a qualidade agregada do agente cai abaixo do limiar, o loop sugere:

- reduzir `max_recommendations`
- aumentar foco em precisao

## Integracao com outros modulos

### Decision Engine

- `DecisionExecutionService` mede `DecisionOutcome` apos sucesso ou falha
- outcomes consomem policy aplicada, explainability e status da execucao

### Simulation Engine

- `SimulationOrchestrator` mede `SimulationOutcome` ao concluir a simulacao
- o loop compara o previsto com o realizado quando houver decisao associada

### Agents Center

- qualidade por agente considera runs, recommendations e decisions
- proposals podem ajustar `AgentExecutionPolicy`

### Copilot

- feedback pode ser registrado para `ManagerCopilotMessage`
- o copilot passa a exibir sinais recentes de optimization e quality

## Observabilidade

Eventos emitidos:

- `optimization.feedback.received`
- `optimization.outcome.measured`
- `optimization.effectiveness.scored`
- `optimization.proposal.created`
- `optimization.proposal.approved`
- `optimization.proposal.rejected`
- `optimization.adjustment.applied`

## Admin Shell

Tela: `/app/ai-agents/optimization/`

Mostra:

- quality overview
- quality por agente
- quality do copilot
- outcomes recentes
- feedbacks recentes
- proposals pendentes e recentes

## API interna

Base: `/api/v1/ai-optimization/`

- `POST /feedbacks/`
- `GET /recommendation-outcomes/`
- `GET /decision-outcomes/`
- `GET /decision-outcomes/{public_id}/comparison/`
- `GET /simulation-outcomes/`
- `GET /proposals/`
- `POST /proposals/{public_id}/approve/`
- `POST /proposals/{public_id}/reject/`
- `POST /proposals/generate/`
- `GET /policies/`
- `GET /quality/agents/`
- `GET /quality/copilots/`

## Limitacoes atuais

- heuristicas de outcome ainda sao deterministicas
- parte dos outcomes depende do artefato criado pela execucao, nao do desempenho longitudinal completo
- feedback do copilot nesta rodada e centrado no gestor
- ajustes sao supervisionados, mas ainda nao existe workflow multi-step

## Proximos passos

- scoring longitudinal por tenant/segmento
- bandit strategies supervisionadas
- calibration loop com janelas temporais reais
- proposals em lote e multi-step approval
- tuning especifico por agente, cliente e criticidade
