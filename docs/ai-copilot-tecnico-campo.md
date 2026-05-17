# AI Copilot para Tecnico em Campo

## Objetivo

O `AI Copilot para Tecnico em Campo` entrega suporte rapido e contextual ao tecnico durante a execucao da OS, com leitura de historico, sugestao de diagnostico, interpretacao de checklist, apoio ao registro tecnico e fallback offline.

## Arquitetura

Camadas principais:

- `TechnicianCopilotService`: classifica intencao, resolve contexto da OS/ativo e compoe respostas curtas.
- `TechnicianCopilotSession` e `TechnicianCopilotMessage`: sessao auditavel do tecnico.
- `get_technician_copilot_bootstrap`: envia contexto inicial para o app/PWA.
- endpoints moveis em `/field/api/copilot/...`
- `technician-copilot.js`: drawer, cache local, fallback offline e sync da conversa.

## Contexto utilizado

O copiloto combina:

- OS atual
- ativo atual
- historico recente do ativo
- falhas recentes
- checklist atual e itens NOK
- materiais/pecas do atendimento
- recomendacoes do `Maintenance Intelligence Agent`

## Intents suportadas

- `history_summary`
- `diagnostic_hint`
- `execution_guidance`
- `checklist_interpretation`
- `documentation_help`
- `parts_suggestion`

## Endpoints

- `GET /field/api/copilot/context/?order_code=...`
- `GET /field/api/copilot/suggestions/?order_code=...`
- `POST /field/api/copilot/query/`
- `POST /field/api/copilot/sync/`

## Fluxo offline

1. A tela carrega `technician_copilot_bootstrap`.
2. O JS salva contexto e historico curto no `localStorage`.
3. Sem conexao, o copiloto responde com fallback baseado no ultimo contexto da OS.
4. Ao voltar online, o JS envia as mensagens offline para `copilot/sync`.

## Observabilidade

Eventos registrados:

- `copilot.tech.query.received`
- `copilot.tech.context.loaded`
- `copilot.tech.response.generated`
- `copilot.tech.offline.mode`
- `copilot.tech.sync.completed`

## Limites atuais

- heuristicas deterministicas, sem LLM externo
- fallback offline depende do ultimo contexto sincronizado da OS
- sugestao de peca baseada em materiais historicos e contexto local
- sem voz, imagem ou multimodalidade nesta rodada

## Evolucao futura

- entrada por voz
- analise de imagem/painel
- diagnostico assistido mais profundo
- sugestao automatica de peca por familia de ativo
- integracao com sensores e IoT
