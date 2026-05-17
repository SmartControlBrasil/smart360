# AI Knowledge Graph Industrial e Operacional

## Visao Geral
O Knowledge Graph do SMART360 consolida memoria relacional do ecossistema sobre uma estrutura projetada em banco relacional. Ele conecta ativos, categorias, falhas, causas, ordens, preventivas, pecas, tecnicos, skills, contratos, recomendacoes, decisoes, anomalias e marketplace.

## Componentes
- `GraphNode`
- `GraphEdge`
- `GraphProjectionRun`
- `GraphProjectionService`
- `GraphQueryService`
- `GraphInsightService`

## Tipos iniciais de nos
- `asset`
- `asset_category`
- `failure_event`
- `failure_mode`
- `rca_cause`
- `preventive_plan`
- `work_order`
- `checklist`
- `checklist_item`
- `part`
- `technician`
- `skill`
- `company`
- `site`
- `contract`
- `quote`
- `recommendation`
- `decision`
- `anomaly`
- `service_request`
- `assignment`

## Relacoes iniciais
- `asset_located_at_site`
- `asset_belongs_to_category`
- `asset_has_failure`
- `failure_has_mode`
- `failure_has_cause`
- `work_order_targets_asset`
- `work_order_generated_from_failure`
- `preventive_targets_asset`
- `checklist_used_in_work_order`
- `checklist_item_flagged_issue`
- `part_used_in_work_order`
- `part_related_to_asset`
- `technician_has_skill`
- `technician_executed_work_order`
- `technician_best_fit_for_category`
- `contract_covers_asset`
- `company_owns_site`
- `company_has_contract`
- `recommendation_targets_asset`
- `decision_acts_on_entity`
- `anomaly_detected_on_entity`
- `assignment_allocates_technician`
- `service_request_targets_asset`
- `service_request_linked_to_site`

## Fluxo de projeção
1. O projector varre o escopo `company/site`.
2. Registros operacionais viram `GraphNode`.
3. Dependencias e histórico viram `GraphEdge`.
4. Um `GraphProjectionRun` registra a execução.
5. Eventos do `Real-Time Event Bus` disparam refresh incremental orientado a escopo.

## Queries implementadas
- `related_failures(asset_id)`
- `related_parts(asset_id | failure_mode)`
- `related_technicians(asset_id | category_slug)`
- `related_work_orders(asset_id | failure_mode)`
- `related_recommendations(entity)`
- `related_decisions(entity)`
- `related_sites(company)`
- `related_contracts(asset | site)`
- `related_anomalies(entity)`
- `neighbors(node, hops)`
- `entity_context(entity)`
- `explanation_path(from, to, max_hops)`

## Integracoes
- `Maintenance Agent`: falhas, causas, tecnicos e pecas passam a ter contexto relacional recuperavel
- `Manager Copilot`: cards de `Graph Insight` no contexto ativo
- `Digital Twin`: bloco de `Graph Insight` no twin selecionado
- `Real-Time Event Bus`: subscriber `knowledge_graph_projection_refresh`
- `Decision / Simulation`: base pronta para recuperar contexto semelhante antes da acao

## Endpoints
- `GET /api/v1/ai-knowledge-graph/nodes/`
- `GET /api/v1/ai-knowledge-graph/nodes/context/`
- `GET /api/v1/ai-knowledge-graph/nodes/{public_id}/neighbors/`
- `GET /api/v1/ai-knowledge-graph/nodes/{public_id}/insights/`
- `GET /api/v1/ai-knowledge-graph/nodes/explanation-path/`
- `GET /api/v1/ai-knowledge-graph/nodes/subgraph/`
- `GET /api/v1/ai-knowledge-graph/edges/`
- `GET /api/v1/ai-knowledge-graph/projection-runs/`
- `POST /api/v1/ai-knowledge-graph/projection-runs/rebuild/`

## Shell
- `GET /app/ai-agents/knowledge-graph/`

## Limitacoes atuais
- o grafo ainda e projetado em camada relacional, nao em engine de grafo especializada
- caminhos multi-hop ainda sao simples e limitados
- ainda nao existe embedding relacional nem busca semantica sobre o grafo
- relacoes com reports e RCA estruturado podem ser aprofundadas em rodadas seguintes

## Proximos passos recomendados
- ranking mais sofisticado de similaridade contextual
- raciocinio por caminhos com pesos adaptativos
- graph embeddings e retrieval semantico
- graph + digital twin em tempo real
- graph como contexto universal de copilots e agents
