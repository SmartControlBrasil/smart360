# AI Automation Center

## Visao do modulo

O `ai_automation_center` prepara o ecossistema SMART360 para tarefas de IA, automacoes inteligentes, prompts versionados, execucoes rastreaveis, artefatos gerados, anotacao humana e futura integracao com RAG, embeddings e copilotos.

## Entidades

- `AITaskType`
- `PromptTemplate`
- `PromptVersion`
- `AIContextProfile`
- `AITaskRequest`
- `AITaskExecution`
- `AIGeneratedArtifact`
- `AutomationRule`
- `AutomationExecution`
- `AIAnnotation`
- `RetrievalSourceConfig`
- `AIModelConfig`

## Fluxo de task request

1. definir `AITaskType`
2. criar `PromptTemplate` e snapshot em `PromptVersion`
3. opcionalmente associar `AIContextProfile`
4. abrir `AITaskRequest`
5. executar a tarefa e registrar `AITaskExecution`
6. persistir a saida utilizavel em `AIGeneratedArtifact`
7. opcionalmente revisar com `AIAnnotation`

## Fluxo de execution

Nesta rodada, a execucao usa modo `simulated`, mas a estrutura suporta provider, modelo, prompt snapshot, input snapshot, tokens e custo. Isso deixa o modulo pronto para acoplar um executor real depois.

## Generated Artifacts

`AIGeneratedArtifact` representa o que o restante do ecossistema pode reaproveitar:

- resumo
- classificacao
- tags sugeridas
- campos extraidos
- copy inicial
- recomendacoes

## Automacoes

`AutomationRule` conecta `trigger_event`, tipo de tarefa e prompt. `AutomationExecution` registra o disparo real. O design foi preparado para receber eventos do `integration_bus`.

## Preparacao para RAG

`RetrievalSourceConfig` organiza futuras fontes de recuperacao como:

- artigos do `knowledge_engine`
- documentos do `files_center`
- notas do `crm_center`
- historicos operacionais

## Integracao com modulos do ecossistema

O modulo foi preparado para atender:

- `smart_site_factory`
- `growth_engine`
- `smart_system`
- `marketplace_technicians`
- `marketplace_analytical`
- `knowledge_engine`
- `notification_center`
- `reporting_center`
- `integration_bus`
- `analytics_platform`
- `files_center`
- `global_search`

O workspace atual nao possui `crm_center`; a integracao foi deixada preparada conceitualmente por `source_module`, `source_reference_type` e `source_reference_id`.

## Endpoints criados

- `GET|POST /api/v1/ai/task-types/`
- `GET|POST /api/v1/ai/prompt-templates/`
- `POST /api/v1/ai/prompt-templates/{id}/preview/`
- `GET|POST /api/v1/ai/prompt-versions/`
- `GET|POST /api/v1/ai/context-profiles/`
- `GET|POST /api/v1/ai/task-requests/`
- `POST /api/v1/ai/task-requests/{id}/run/`
- `GET|POST /api/v1/ai/task-executions/`
- `GET|POST /api/v1/ai/generated-artifacts/`
- `GET|POST /api/v1/ai/automation-rules/`
- `POST /api/v1/ai/automation-rules/{id}/run/`
- `GET|POST /api/v1/ai/automation-executions/`
- `GET|POST /api/v1/ai/annotations/`
- `GET|POST /api/v1/ai/retrieval-source-configs/`
- `GET|POST /api/v1/ai/model-configs/`
- `POST /api/v1/ai/run-task/`
- `GET /api/v1/ai/task-history/`
- `GET /api/v1/ai/automation-history/`
- `POST /api/v1/ai/prompt-preview/`

## Proximos passos

- integrar executor real de LLM
- adicionar embeddings e indexacao vetorial
- integrar eventos do `integration_bus`
- registrar metricas de custo e qualidade em `analytics_platform`
- plugar artifacts no `global_search` e `files_center`
