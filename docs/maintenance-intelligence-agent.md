# Maintenance Intelligence Agent

## Visao geral

O `Maintenance Intelligence Agent` e a primeira inteligencia especializada em engenharia de manutencao dentro do `AI Agents Center`. Ele opera sobre ativos, falhas, preventivas, ordens de servico, checklists, relatorios e snapshots analiticos para identificar degradacao operacional, reincidencia e risco de indisponibilidade.

## Arquitetura

- `apps/ai_agents_center/agents/maintenance.py`
  - adaptador do agente especializado no registry.
- `apps/ai_agents_center/services/maintenance_intelligence.py`
  - builder de contexto consolidado por ativo/site/categoria.
  - heuristicas deterministicas e explicaveis.
  - geracao estruturada de recomendacoes e propostas de acao.
- `apps/ai_agents_center/services/orchestrator.py`
  - persiste runs, recomendacoes, propostas e flags de ativos sob atencao.
  - registra observabilidade especifica do agente.
- `apps/ai_agents_center/services/maintenance_triggers.py`
  - centraliza disparos manuais, por evento e agendados.

## Fontes de dados

- `smart_system.Asset`
- `smart_system.FailureEvent`
- `smart_system.ServiceOrder`
- `smart_system.MaintenancePlan`
- `smart_system.ServiceOrderChecklistResponse`
- `smart_system.ServiceDocument` com `document_type=report`
- `reporting_center.ReportRequest`
- `analytics_platform.OperationalMetrics`
- `analytics_platform.AnalyticsSnapshot`

## Heuristicas implementadas

- reincidencia de falhas acima do limiar por janela configuravel
- repeticao do mesmo modo de falha
- ativo critico com preventiva vencida e aderencia preventiva baixa
- aumento recente de intervencoes em comparacao com a janela anterior
- sequencia de checklists com NOK
- deterioracao de MTBF
- plano preventivo possivelmente insuficiente
- risco de indisponibilidade por parada acumulada, criticidade e empilhamento de sinais

Os limiares ficam em `AgentDefinition.config.heuristics` e o bootstrap do registry ja inicializa valores base para o agente.

## Recommendation types

- `failure_pattern_alert`
- `critical_asset_watch`
- `extraordinary_inspection`
- `preventive_review`
- `reliability_attention`
- `action_plan_recommendation`

Cada recomendacao persiste:

- tipo
- severidade
- prioridade
- resumo
- explicacao
- evidencias resumidas
- acao sugerida
- score de atencao
- necessidade de aprovacao humana

## Action proposal types

- `open_inspection_work_order`
- `review_preventive_plan`
- `mark_asset_under_watch`
- `create_technical_analysis`
- `review_checklist_strategy`
- `reevaluate_preventive_frequency`

Todas ficam em `pending_approval` por padrao e usam o fluxo existente de aprovacao/rejeicao do `AI Agents Center`.

## Triggers

### Event-based

- falha registrada
- OS alterada para aberta ou concluida

### Schedule-based

- `python manage.py run_maintenance_agent --mode daily_critical_assets`
- `python manage.py run_maintenance_agent --mode weekly_failure_recurrence`
- `python manage.py run_maintenance_agent --mode preventive_adherence`
- `python manage.py run_maintenance_agent --mode reliability_review`

### Manual / API

- `POST /api/v1/ai-agents/manual-run/`
- `POST /api/v1/ai-agents/maintenance/run/`

## Endpoints relevantes

- `GET /api/v1/ai-agents/recommendations/?agent_slug=maintenance-agent`
- `GET /api/v1/ai-agents/recommendations/?agent_slug=maintenance-agent&asset=<asset_public_id>`
- `GET /api/v1/ai-agents/recommendations/?agent_slug=maintenance-agent&category=<category_slug>`
- `GET /api/v1/ai-agents/action-proposals/?agent_slug=maintenance-agent`
- `GET /api/v1/ai-agents/runs/?agent_slug=maintenance-agent`
- `GET /api/v1/ai-agents/maintenance-attention-assets/`
- `POST /api/v1/ai-agents/maintenance/run/`

## Observabilidade

Eventos especificos registrados:

- `agent.maintenance.run.started`
- `agent.maintenance.run.completed`
- `agent.maintenance.pattern.detected`
- `agent.maintenance.recommendation.created`
- `agent.maintenance.action.proposed`
- `agent.maintenance.action.approved`
- `agent.maintenance.action.rejected`

Os payloads carregam `company`, `site`, `asset`, `trigger_reference`, `duration_ms`, severidade, prioridade e sinais acionados.

## Interfaces administrativas

- dashboard do `AI Agents Center` com resumo e watchlist de ativos
- tela de recomendacoes com explicacao e acao sugerida
- tela de `Maintenance Health` com ativos em observacao
- tela de propostas com aprovacao/rejeicao humana

## Limites atuais

- heuristicas ainda sao deterministicas, sem modelo probabilistico
- o score de saude do ativo ainda nao e persistido como entidade independente
- relatorios tecnicos usam documentos e requests recentes; ainda nao existe leitura semantica do conteudo
- gatilho de checklist concluido depende do estado persistido em `ServiceOrderChecklistResponse`

## Proximos passos recomendados

- persistir score historico de saude por ativo
- acoplar sensores e telemetria IoT
- adicionar inferencia probabilistica de falha
- sugerir ajuste assistido de frequencia preventiva por familia de ativos
- integrar conhecimento do RCA e knowledge engine para recomendacoes mais profundas
