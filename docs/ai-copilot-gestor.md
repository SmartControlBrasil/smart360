# AI Copilot para Gestor

## Objetivo

O `AI Copilot para Gestor` entrega uma interface conversacional e analitica acoplada ao contexto real do SMART360. Ele responde perguntas sobre operacao, agenda, rentabilidade, marketplace e anomalias usando o tenant/site ativo, recomendacoes dos agentes e KPIs consolidados.

## Arquitetura

Fluxo principal:

1. UI do Admin Shell envia a consulta.
2. `ManagerCopilotService` classifica a intencao.
3. O contexto atual e resolvido com tenant, site, periodo, entidade em foco e memoria curta da sessao.
4. O copiloto agrega recomendacoes e propostas dos agentes especializados.
5. O `response composer` monta resumo, prioridades, cards de risco, cards de recomendacao, propostas pendentes e links internos.
6. Sessao e mensagens ficam persistidas e auditaveis.

Componentes principais:

- `ManagerCopilotConfiguration`: configuracao global ou por empresa.
- `ManagerCopilotSession`: sessao curta e auditavel do gestor.
- `ManagerCopilotMessage`: historico estruturado da conversa.
- `ManagerCopilotService`: classificacao de intencao, resolucao de contexto, agregacao e composicao da resposta.
- API protegida do copiloto.
- Tela dedicada no `Admin Shell`.

## Intents suportadas

- `executive_summary`
- `comparison`
- `risk_anomaly`
- `profitability`
- `scheduling`
- `maintenance`
- `marketplace`
- `recommendation_action`
- `investigation`

## Respostas estruturadas

O copiloto pode retornar:

- resumo executivo
- prioridades operacionais
- cards de risco
- cards de recomendacao
- propostas pendentes
- comparacao de periodo
- links internos para telas relevantes

## Contexto e seguranca

O copiloto respeita:

- empresa ativa
- unidade ativa
- memberships do usuario
- filtros por ativo, cliente, contrato e tecnico
- aprovacao humana para propostas sensiveis

Nenhum dado fora do tenant ativo deve aparecer na resposta.

## Integracao com agentes

O copiloto consulta:

- `Maintenance Intelligence Agent`
- `Scheduling Optimization Agent`
- `Profitability Agent`
- `Marketplace Allocation Agent`
- `Anomaly Detection Agent`

Ele combina recomendacoes e propostas existentes, remove duplicacoes obvias e prioriza itens por severidade, prioridade e score de atencao.

## Endpoints

- `POST /api/v1/ai-agents/copilot/query/`
- `GET /api/v1/ai-agents/copilot/context/`
- `GET /api/v1/ai-agents/copilot/suggestions/`
- `GET /api/v1/ai-agents/copilot/recommendations/`
- `GET /api/v1/ai-agents/copilot/sessions/`
- `GET /api/v1/ai-agents/copilot/sessions/<id>/history/`
- `POST /api/v1/ai-agents/copilot/sessions/<id>/reset/`
- `POST /api/v1/ai-agents/copilot/proposals/<id>/approve/`
- `POST /api/v1/ai-agents/copilot/proposals/<id>/reject/`

## Observabilidade

Eventos registrados:

- `copilot.manager.query.received`
- `copilot.manager.context.resolved`
- `copilot.manager.response.generated`
- `copilot.manager.action.suggested`
- `copilot.manager.proposal.approved`
- `copilot.manager.proposal.rejected`

## Limites atuais

- classificacao de intencao deterministica por heuristica
- memoria curta por sessao, sem memoria longa automatica
- comparacao temporal simplificada
- respostas baseadas em dados estruturados e recomendacoes existentes, nao em LLM externo

## Proximos passos

- copiloto por persona
- briefing automatico diario/semanal
- explicacoes mais ricas por recomendacao
- benchmark interno entre unidades e contratos
- automacoes supervisionadas com playbooks
