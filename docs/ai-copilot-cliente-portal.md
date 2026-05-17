# AI Copilot para Cliente / Portal

## Visao geral

O `AI Copilot para Cliente` foi implementado como uma camada segura de leitura e explicacao dentro do `Portal do Cliente`.
Ele responde com base no mesmo contexto ja exposto no portal:

- tenant/company ativo
- site/unidade ativa
- ativos visiveis
- ordens de servico
- preventivas
- relatorios
- orcamentos
- contratos
- solicitacoes do cliente

O foco desta primeira versao e clareza, transparencia e autosservico assistido.

## Arquitetura

### Componentes principais

- `ClientPortalCopilotService`
  - classificador deterministico de intencao
  - resolvedor de contexto por ativo/OS/preventiva/relatorio/orcamento/contrato
  - composer de resposta
  - sessao curta com memoria auditavel
  - integracao com observabilidade
- `ClientPortalSafeResponsePolicy`
  - bloqueia termos e temas internos sensiveis
  - filtra recommendations internas nao apropriadas ao cliente
- `ClientPortalCopilotSession` e `ClientPortalCopilotMessage`
  - persistem conversa, contexto e payload estruturado
- tela dedicada no portal
  - conversa atual
  - sugestoes
  - pendencias
  - cards de contexto

## Fluxo

1. Cliente entra no portal ou abre o copiloto a partir de um contexto.
2. O frontend envia pergunta e contexto semente.
3. O service resolve escopo seguro no tenant/site do usuario.
4. A policy segura filtra respostas e recommendations.
5. O composer retorna:
   - `summary`
   - `bullets`
   - `cards`
   - `actions`
6. A sessao e as mensagens ficam auditaveis.

## Intents suportadas

- `site_summary`
- `asset_summary`
- `work_order_status`
- `preventive_status`
- `report_explanation`
- `quote_explanation`
- `pending_actions`
- `comparison`

## Tipos de resposta

- resumo operacional
- explicacao de status
- explicacao de relatorio
- explicacao de orcamento
- visao por ativo
- comparacao simples de periodo
- proximos passos e pendencias

## Safe response policy

O copiloto nao deve expor:

- margem
- lucro
- prejuizo
- rentabilidade
- custo interno
- notas internas
- auditoria interna
- recomendações gerenciais nao destinadas ao cliente
- dados fora do tenant/site autorizado

Nesta versao, recommendations internas so aparecem quando forem seguras e orientadas ao cliente, principalmente manutencao/anomalia em linguagem neutra.

## Endpoints

- `GET /portal/copilot/`
- `GET /portal/api/copilot/context/`
- `GET /portal/api/copilot/suggestions/`
- `GET /portal/api/copilot/pending/`
- `POST /portal/api/copilot/query/`

## Observabilidade

Eventos registrados:

- `copilot.client.query.received`
- `copilot.client.context.resolved`
- `copilot.client.response.generated`
- `copilot.client.action.suggested`
- `copilot.client.document.explained`

## Limites atuais

- comparacao temporal ainda e simples, baseada em janelas curtas
- sem LLM generativa; a camada e deterministica e rastreavel
- explicacao de relatorio resume secoes publicadas, sem inferencia profunda
- aprovacao de orcamento continua no fluxo normal do portal; o copiloto orienta, nao executa

## Proximos passos

- copiloto white-label por tenant
- explicacao mais personalizada por perfil do cliente
- prompts proativos por pagina/unidade
- integracao hibrida com suporte humano
- resumo automatico semanal do portal
