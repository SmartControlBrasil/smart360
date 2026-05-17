# AI Briefings Automaticos

## Visao geral

O sistema de `AI Briefings` gera resumos automaticos, periodicos e sob demanda para:

- gestores
- tecnicos em campo
- clientes do portal

Os briefings usam dados reais do SMART360 e consolidam sinais dos agentes:

- Maintenance Intelligence Agent
- Scheduling Optimization Agent
- Profitability Agent
- Marketplace Allocation Agent
- Anomaly Detection Agent

## Tipos implementados

- `daily_executive`
- `daily_field`
- `daily_client`
- `weekly_executive`
- `on_demand`

## Arquitetura

### Modelos

- `AIBriefingConfiguration`
- `AIBriefing`
- `AIBriefingDelivery`

### Servicos

- `AIBriefingComposer`
  - coleta contexto
  - agrega recomendações/proposals
  - gera payload estruturado
  - entrega via dashboard/portal/field/in-app

### Jobs

- `ai_agents_center.generate_daily_executive_briefings`
- `ai_agents_center.generate_daily_field_briefings`
- `ai_agents_center.generate_daily_client_briefings`
- `ai_agents_center.generate_weekly_executive_briefings`

## Scheduler

Configurado em `config/celery.py`:

- diario 07:00
  - executivo
  - tecnico
  - cliente
- semanal segunda 08:00
  - executivo

## Delivery channels

Implementados:

- `dashboard`
- `portal`
- `field_app`
- `in_app`

Preparados:

- `email`
- `push`

## Historico e consulta

Os briefings ficam persistidos com:

- tipo
- audiencia
- company/site/user
- periodo
- payload completo
- recommendations/proposals de origem
- status de entrega e visualizacao

## Interfaces

- Admin Shell
  - lista de briefings
  - detalhe do briefing
  - geracao sob demanda
- Portal do Cliente
  - card com briefing do dia
  - detalhe do briefing
- App Tecnico
  - card com briefing do dia
  - detalhe do briefing

## API

- `GET /api/v1/ai-agents/briefings/`
- `POST /api/v1/ai-agents/briefings/generate/`
- `POST /api/v1/ai-agents/briefings/<uuid>/viewed/`

## Observabilidade

Eventos:

- `briefing.generated`
- `briefing.delivered`
- `briefing.viewed`

## Integracao com copilots

Nesta rodada:

- copilotos passam a ter briefings persistidos disponiveis como base de leitura
- dashboards do portal e app tecnico exibem o briefing do dia
- o gestor tem area dedicada de consulta no AI Agents Center

## Limites atuais

- o weekly summary ainda usa agregacao deterministica simples
- email e push estao preparados, mas nao possuem dispatcher externo real
- personalizacao por idioma ainda nao foi implementada
- os briefings nao usam LLM generativa; a composicao e transparente e auditavel

## Proximos passos

- briefing em audio
- briefing por WhatsApp/email com templates ricos
- personalizacao por tenant e persona
- resumos preditivos com tendencia futura
- copilots explicando briefing com navegacao contextual mais profunda
