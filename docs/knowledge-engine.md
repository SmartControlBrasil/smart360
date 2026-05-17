# KNOWLEDGE ENGINE

## Visao do modulo

O Knowledge Engine e a base de conhecimento tecnica estruturada do ecossistema SMART360. Ele organiza taxonomia, equipamentos, sintomas, falhas, causas, acoes recomendadas, artigos, documentos e relacoes explicitas para formar um pequeno grafo tecnico reutilizavel.

## Entidades

- `KnowledgeCategory`
- `EquipmentReference`
- `SymptomReference`
- `FailureReference`
- `CauseReference`
- `RecommendedAction`
- `TroubleshootingArticle`
- `TechnicalDocument`
- `KnowledgeTag`
- `KnowledgeLinkRule`
- `EquipmentSymptomMap`
- `SymptomFailureMap`
- `FailureCauseMap`
- `FailureActionMap`
- `KnowledgeFeedback`

## Taxonomia tecnica

- categorias aceitam hierarquia simples com `parent`
- equipamentos, sintomas, falhas, causas e acoes sao entidades independentes
- relacoes tecnicas ficam explicitadas em tabelas de mapa e link rules

## Relacoes entre symptom / failure / cause / action

1. `EquipmentSymptomMap` relaciona contexto de equipamento e sintoma
2. `SymptomFailureMap` liga sintoma a falhas provaveis
3. `FailureCauseMap` liga falha a causas provaveis
4. `FailureActionMap` liga falha a acoes recomendadas

## Fluxo de uso futuro com smart_system e marketplaces

- `smart_system` podera consultar equipamentos, sintomas, falhas, acoes e documentos para apoiar OS e diagnosticos
- `marketplace_technicians` podera usar artigos, procedimentos e troubleshooting durante execucao
- `marketplace_analytical` podera enriquecer diagnosticos e laudos com referencias tecnicas
- o modulo fica preparado para busca semantica, RAG e indexacao futura

## Endpoints criados

- `GET|POST /api/v1/knowledge/categories/`
- `GET|POST /api/v1/knowledge/equipments/`
- `GET|POST /api/v1/knowledge/symptoms/`
- `GET|POST /api/v1/knowledge/failures/`
- `GET|POST /api/v1/knowledge/causes/`
- `GET|POST /api/v1/knowledge/recommended-actions/`
- `GET|POST /api/v1/knowledge/troubleshooting-articles/`
- `GET|POST /api/v1/knowledge/technical-documents/`
- `GET|POST /api/v1/knowledge/tags/`
- `GET|POST /api/v1/knowledge/link-rules/`
- `GET|POST /api/v1/knowledge/equipment-symptom-maps/`
- `GET|POST /api/v1/knowledge/symptom-failure-maps/`
- `GET|POST /api/v1/knowledge/failure-cause-maps/`
- `GET|POST /api/v1/knowledge/failure-action-maps/`
- `GET|POST /api/v1/knowledge/feedback/`
