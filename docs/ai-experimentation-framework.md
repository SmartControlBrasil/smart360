# AI Experimentation Framework

O `AI Experimentation Framework` do SMART360 cria uma camada auditavel para testes A/B/C de agentes, copilotos, heuristicas, policies e motores de decisao/simulacao.

## Arquitetura

Fluxo principal:

1. experimento e criado com variantes e metrica principal
2. runtime resolve assignment consistente por entidade/caso
3. variante escolhida e anexada ao contexto operacional
4. metricas reais sao registradas por variante
5. resultado comparativo e consolidado
6. variante vencedora pode ser promovida
7. promocao gera evidencia para o Auto-Optimization Loop

## Modelos principais

- `Experiment`: define alvo, tenant, estrategia de distribuicao, metrica principal e criterio de sucesso
- `Variant`: configuracao concorrente de estrategia A/B/C
- `ExperimentAssignment`: garante consistencia de variante por entidade/caso
- `ExperimentMetric`: coleta resultados observados no runtime
- `ExperimentResult`: consolida comparacao, confianca e recomendacao
- `ExperimentAuditTrail`: auditoria do ciclo inteiro

## Tipos de experimento suportados

- matching strategy A vs B
- routing heuristic A vs B
- decision policy strict vs relaxed
- simulation heuristic baseline vs variant
- copilot phrasing/strategy A vs B
- ranking heuristics A vs B

## Estrategias de assignment

- `weighted`: split deterministico ponderado por hash
- `random`: representado como weighted uniforme
- `rule_based`: regras explicitas por contexto antes do fallback ponderado

## Metricas suportadas

- `sla`
- `travel_delta`
- `cost_delta`
- `profit_delta`
- `acceptance_rate`
- `decision_effectiveness_score`
- `simulation_effectiveness_score`
- `agent_run_duration_ms`
- `agent_recommendation_count`

## Integracoes

### Agents Center

- experimentos podem atuar por `agent_slug`
- contexto do `AgentRun` recebe a variante escolhida
- duracao, volume de recomendacoes e volume de proposals viram metricas experimentais

### Decision Engine

- experimentos podem atuar por `normalized_action_type`
- a decisao recebe `experiment` no `explainability_payload`
- sucesso, falha e duracao da execucao alimentam metricas reais

### Simulation Engine

- experimentos podem atuar por `simulation_type`
- impacto e duracao das simulacoes sao coletados por variante

### Auto-Optimization Loop

- outcomes de decisao e simulacao viram metricas de efetividade experimental
- promocao de variante vencedora gera `OptimizationProposal`

### Policy Studio

- criacao de experimento
- assignment de variante
- coleta de metricas
- conclusao
- promocao

Todos esses pontos passam por `PolicyStudioEngine`.

## API

- `GET/POST /api/v1/ai-experiments/experiments/`
- `POST /api/v1/ai-experiments/experiments/{public_id}/assign/`
- `POST /api/v1/ai-experiments/experiments/{public_id}/record_metric/`
- `GET /api/v1/ai-experiments/experiments/{public_id}/analysis/`
- `POST /api/v1/ai-experiments/experiments/{public_id}/complete/`
- `POST /api/v1/ai-experiments/experiments/{public_id}/promote/`

## Admin Shell

- `/app/ai-agents/experiments/`

Mostra:

- experimentos ativos
- resultados comparativos
- assignments recentes
- metricas recentes

## Observabilidade

Eventos emitidos:

- `experiment.created`
- `variant.assigned`
- `metric.recorded`
- `experiment.completed`
- `variant.promoted`

## Limitacoes atuais

- comparacao estatistica ainda e heuristica, sem teste formal de significancia
- `rule_based` ainda usa matching simples por igualdade de contexto
- auto-promotion continua bloqueada por policy de alto risco
- a promocao ainda gera proposal supervisionada, nao mudanca silenciosa

## Proximos passos

- multi-armed bandit supervisionado
- significancia estatistica formal
- janelas adaptativas por tenant/segmento
- experimentos multi-step
- promotion pipelines com rollout progressivo
